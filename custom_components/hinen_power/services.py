"""Service registration and handlers for Hinen Power integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from hinen_open_api.exceptions import HinenBackendError, UnauthorizedError
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import (
    AUTH,
    CD_PERIOD_TIMES2,
    CD_PERIOD_WEEK_SUPPORT,
    COORDINATOR,
    DOMAIN,
    PERIOD_AC_ENABLE,
    PERIOD_ENABLE,
    PERIOD_POWER,
    PERIOD_SOC,
    PERIOD_START_TIME,
    PERIOD_TIME_END,
    PERIOD_TIME_RATE,
    PERIOD_TIME_START,
    PERIOD_TIME_STOP_SOC,
    PERIOD_WEEK_ENABLE,
    POWER_PROTECTION_MODE_TIME_PERIOD,
    PROPERTIES,
    SERVICE_SET_PERIOD_TIMES2,
    SERVICE_SET_POWER_PROTECTION_MODE_TIME_PERIOD,
)
from .utils import extract_property_specs, extract_property_value

_LOGGER = logging.getLogger(__name__)
_WEEKDAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


# --- Schemas ---

_PERIOD_SCHEMA = vol.Schema({
    vol.Required(PERIOD_ENABLE): vol.In([0, 1]),
    vol.Required(PERIOD_WEEK_ENABLE): cv.string,
    vol.Required(PERIOD_TIME_START): int,
    vol.Required(PERIOD_TIME_END): int,
    vol.Required(PERIOD_TIME_RATE): int,
    vol.Required(PERIOD_TIME_STOP_SOC): int,
})

SERVICE_SET_PERIOD_TIMES2_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Required("periods"): vol.All(
        list,
        vol.Length(max=20),
        [_PERIOD_SCHEMA],
    ),
})

# Power Protection periods: range validation is handled by
# _validate_power_protection_periods using device specs (no hardcoded fallbacks).
# PERIOD_AC_ENABLE: enum 0/1; PERIOD_START_TIME: minutes in 24h (intrinsic time semantics).
_POWER_PROTECTION_PERIOD_SCHEMA = vol.Schema({
    vol.Required(PERIOD_SOC): int,
    vol.Required(PERIOD_AC_ENABLE): int,
    vol.Required(PERIOD_START_TIME): int,
    vol.Required(PERIOD_POWER): int,
})

SERVICE_SET_POWER_PROTECTION_MODE_TIME_PERIOD_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Required("periods"): vol.All(
        list,
        vol.Length(max=20),
        [_POWER_PROTECTION_PERIOD_SCHEMA],
    ),
})


# --- Validation helpers ---

def _parse_week_enable(week_str: str) -> list[int]:
    """Parse PeriodWeekEnable string to list of ints.

    Args:
        week_str: Comma-separated string of 0/1 values (e.g. "1,0,1,1,1,0,0")

    Returns:
        List of ints (length 7 for Mon-Sun).

    Raises:
        ServiceValidationError: If the string is not valid comma-separated 0/1 values.
    """
    if not week_str:
        return []
    try:
        values = [int(x) for x in week_str.split(",")]
    except ValueError:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_week_enable",
            translation_placeholders={"value": week_str},
        ) from None
    if len(values) != 7 or not all(v in (0, 1) for v in values):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_week_enable",
            translation_placeholders={"value": week_str},
        )
    return values


def _periods_have_overlap(start1: int, end1: int, start2: int, end2: int) -> bool:
    """Check if two time periods overlap (supports cross-midnight periods)."""
    if start1 > end1:
        end1 += 1440
    if start2 > end2:
        end2 += 1440
    return start1 < end2 and start2 < end1


def _validate_periods(
    periods: list[dict],
    week_support: bool = True,
    device_specs: dict[str, dict[str, int]] | None = None,
) -> None:
    """Validate periods configuration against device specs.

    Args:
        periods: List of period configurations
        week_support: Whether device supports week configuration.
            If False, only check time overlap.
        device_specs: Device specs for precise validation
            (required if periods are enabled). If None, treated as empty.

    Raises:
        ServiceValidationError: If specs are missing or values are out of range.
    """
    specs = device_specs or {}

    for idx, period in enumerate(periods):
        if not period.get(PERIOD_ENABLE):
            continue

        # Refuse to validate if device specs are incomplete.
        # Device specs are the source of truth — never fall back to hardcoded ranges.
        for field in (PERIOD_TIME_RATE, PERIOD_TIME_STOP_SOC):
            spec = specs.get(field) or {}
            if spec.get("min") is None or spec.get("max") is None:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="period_specs_unavailable",
                    translation_placeholders={"field": field},
                )

        # Validate periodTimeRate range
        rate_spec = specs[PERIOD_TIME_RATE]
        rate_val = period.get(PERIOD_TIME_RATE)
        if rate_val is not None and (rate_val < rate_spec["min"] or rate_val > rate_spec["max"]):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="period_rate_out_of_range",
                translation_placeholders={
                    "period_idx": str(idx + 1),
                    "rate": str(rate_val),
                    "rate_min": str(rate_spec["min"]),
                    "rate_max": str(rate_spec["max"]),
                },
            )

        # Validate periodTimeStopSoc range
        soc_spec = specs[PERIOD_TIME_STOP_SOC]
        soc_val = period.get(PERIOD_TIME_STOP_SOC)
        if soc_val is not None and (soc_val < soc_spec["min"] or soc_val > soc_spec["max"]):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="period_soc_out_of_range",
                translation_placeholders={
                    "period_idx": str(idx + 1),
                    "soc": str(soc_val),
                    "soc_min": str(soc_spec["min"]),
                    "soc_max": str(soc_spec["max"]),
                },
            )

        start = period.get(PERIOD_TIME_START, 0)
        end = period.get(PERIOD_TIME_END, 0)

        # Check start < end
        if start >= end:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="period_start_after_end",
                translation_placeholders={
                    "period_idx": str(idx + 1),
                    "start": str(start),
                    "end": str(end),
                },
            )

        # Check overlap with other enabled periods
        week1: list[int] = []
        if week_support:
            week1 = _parse_week_enable(period.get(PERIOD_WEEK_ENABLE, ""))
        for other_idx, other in enumerate(periods):
            if other_idx <= idx or not other.get(PERIOD_ENABLE):
                continue
            other_start = other.get(PERIOD_TIME_START, 0)
            other_end = other.get(PERIOD_TIME_END, 0)
            if not _periods_have_overlap(start, end, other_start, other_end):
                continue

            if week_support:
                week2 = _parse_week_enable(other.get(PERIOD_WEEK_ENABLE, ""))
                overlap_days = [
                    _WEEKDAY_NAMES[day_idx] if day_idx < len(_WEEKDAY_NAMES) else str(day_idx)
                    for day_idx, (w1, w2) in enumerate(zip(week1, week2))
                    if w1 == 1 and w2 == 1
                ]
                if not overlap_days:
                    continue  # Time overlaps but no shared weekdays
                weekday = ", ".join(overlap_days)
            else:
                weekday = "Every day"

            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="period_overlap",
                translation_placeholders={
                    "period1": str(idx + 1),
                    "period2": str(other_idx + 1),
                    "weekday": weekday,
                    "start1": str(start),
                    "end1": str(end),
                    "start2": str(other_start),
                    "end2": str(other_end),
                },
            )


def _validate_power_protection_periods(
    periods: list[dict],
    device_specs: dict[str, dict[str, int]],
) -> None:
    """Validate power protection periods configuration against device specs.

    Args:
        periods: List of period configurations
        device_specs: Per-field specs from device, keyed by field identifier
            (e.g. {"PeriodSOC": {"min": 10, "max": 100}, ...}).

    Raises:
        ServiceValidationError: If specs are missing or values are out of range.
    """
    # Refuse to validate if device specs are incomplete.
    # Device specs are the source of truth — never fall back to hardcoded ranges.
    for field in (PERIOD_SOC, PERIOD_POWER):
        spec = device_specs.get(field) or {}
        if "min" not in spec or "max" not in spec:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="power_protection_specs_unavailable",
                translation_placeholders={"field": field},
            )

    soc_spec = device_specs[PERIOD_SOC]
    power_spec = device_specs[PERIOD_POWER]

    for idx, period in enumerate(periods):
        soc = period.get(PERIOD_SOC, 0)
        if not soc_spec["min"] <= soc <= soc_spec["max"]:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="power_protection_soc_out_of_range",
                translation_placeholders={
                    "period_idx": str(idx + 1),
                    "soc": str(soc),
                    "soc_min": str(soc_spec["min"]),
                    "soc_max": str(soc_spec["max"]),
                },
            )

        power = period.get(PERIOD_POWER, 0)
        if not power_spec["min"] <= power <= power_spec["max"]:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="power_protection_power_out_of_range",
                translation_placeholders={
                    "period_idx": str(idx + 1),
                    "power": str(power),
                    "power_min": str(power_spec["min"]),
                    "power_max": str(power_spec["max"]),
                },
            )


# --- Common handlers ---

def _find_entry_data_for_device(hass: HomeAssistant, device_id: str) -> dict:
    """Find entry data containing the given device_id.

    Args:
        hass: Home Assistant instance
        device_id: Device identifier to search for

    Returns:
        The entry_data dict containing AUTH and COORDINATOR for this device

    Raises:
        ServiceValidationError: If device_id is not found in any entry
    """
    for entry_data in hass.data.get(DOMAIN, {}).values():
        if device_id in entry_data[COORDINATOR].data:
            return entry_data

    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="device_not_found",
        translation_placeholders={"device_id": device_id},
    )


async def _write_periods_and_broadcast(
    target_entry_data: dict,
    device_id: str,
    periods: list,
    property_key: str,
    translation_key_failure: str,
    log_context: str,
) -> None:
    """Write periods to device via API and broadcast update to coordinator.

    Args:
        target_entry_data: Entry data containing AUTH and COORDINATOR
        device_id: Device identifier
        periods: List of period configurations to write
        property_key: Property constant (e.g. CD_PERIOD_TIMES2)
        translation_key_failure: Translation key for HomeAssistantError on failure
        log_context: Context string for logging
    """
    hinen_open = await target_entry_data[AUTH].get_resource()
    coordinator = target_entry_data[COORDINATOR]

    try:
        await hinen_open.set_property(periods, device_id, PROPERTIES[property_key])
    except UnauthorizedError as err:
        _LOGGER.error("Auth expired for device %s during %s: %s", device_id, log_context, err)
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key=translation_key_failure,
            translation_placeholders={"error": str(err)},
        ) from err
    except HinenBackendError as err:
        _LOGGER.error("Failed to set %s for device %s: %s", log_context, device_id, err)
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key=translation_key_failure,
            translation_placeholders={"error": str(err)},
        ) from err
    except Exception as err:
        _LOGGER.exception("Unexpected error setting %s for device %s", log_context, device_id)
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key=translation_key_failure,
            translation_placeholders={"error": str(err)},
        ) from err

    # Preserve specs from existing data
    existing_data = coordinator.data.get(device_id, {}).get(property_key, {})
    existing_specs = existing_data.get("specs") if isinstance(existing_data, dict) else None

    coordinator.async_set_updated_data({
        **coordinator.data,
        device_id: {
            **coordinator.data.get(device_id, {}),
            property_key: {"value": periods, "specs": existing_specs},
        },
    })

    _LOGGER.info("Updated %d %s for device %s", len(periods), log_context, device_id)


# --- Service handlers ---

async def _handle_set_period_times2(call: ServiceCall) -> None:
    """Handle set_period_times2 service call."""
    hass = call.hass
    device_id = call.data["device_id"]
    periods_data = call.data["periods"]

    target_entry_data = _find_entry_data_for_device(hass, device_id)

    periods = [dict(p) for p in periods_data]

    # Check if device supports week configuration (CDPeriodWeekSupport: 0 or 1)
    device_data = target_entry_data[COORDINATOR].data.get(device_id, {})
    week_support_prop = device_data.get(CD_PERIOD_WEEK_SUPPORT)
    week_support = bool(extract_property_value(week_support_prop)) if week_support_prop else False

    # If device doesn't support week configuration, force all days enabled
    if not week_support:
        for period in periods:
            period[PERIOD_WEEK_ENABLE] = "1,1,1,1,1,1,1"

    # Extract device-specific specs for precise validation
    period_data_prop = device_data.get(CD_PERIOD_TIMES2)
    device_specs = extract_property_specs(period_data_prop)

    _validate_periods(periods, week_support, device_specs)

    _LOGGER.debug(
        "[Hinen Service] %s values: %s",
        PERIOD_WEEK_ENABLE,
        [(i, p.get(PERIOD_WEEK_ENABLE)) for i, p in enumerate(periods)],
    )

    await _write_periods_and_broadcast(
        target_entry_data,
        device_id,
        periods,
        CD_PERIOD_TIMES2,
        "set_period_failed",
        "period config",
    )


async def _handle_set_power_protection_mode_time_period(call: ServiceCall) -> None:
    """Handle set_power_protection_mode_time_period service call."""
    hass = call.hass
    device_id = call.data["device_id"]
    periods_data = call.data["periods"]

    target_entry_data = _find_entry_data_for_device(hass, device_id)

    periods = [dict(p) for p in periods_data]

    # Extract device-specific specs for precise validation
    pp_data = (
        target_entry_data[COORDINATOR]
        .data.get(device_id, {})
        .get(POWER_PROTECTION_MODE_TIME_PERIOD)
    )
    device_specs = extract_property_specs(pp_data)

    _validate_power_protection_periods(periods, device_specs)

    _LOGGER.debug("[Hinen Service] Power protection periods: %s", periods)

    await _write_periods_and_broadcast(
        target_entry_data,
        device_id,
        periods,
        POWER_PROTECTION_MODE_TIME_PERIOD,
        "set_power_protection_failed",
        "power protection periods",
    )


# --- Registration ---

async def async_register_services(hass: HomeAssistant) -> None:
    """Register all Hinen Power services.

    Idempotent: each service is registered at most once per hass instance,
    guarded by hass.services.has_service().
    """
    if not hass.services.has_service(DOMAIN, SERVICE_SET_PERIOD_TIMES2):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_PERIOD_TIMES2,
            _handle_set_period_times2,
            schema=SERVICE_SET_PERIOD_TIMES2_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_SET_POWER_PROTECTION_MODE_TIME_PERIOD):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_POWER_PROTECTION_MODE_TIME_PERIOD,
            _handle_set_power_protection_mode_time_period,
            schema=SERVICE_SET_POWER_PROTECTION_MODE_TIME_PERIOD_SCHEMA,
        )
