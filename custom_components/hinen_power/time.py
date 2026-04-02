"""Support for Hinen Time entities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Any

from hinen_open_api import HinenOpen
from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    AUTH,
    CD_PERIOD_TIMES2,
    COORDINATOR,
    DOMAIN,
    PERIOD_AC_ENABLE,
    PERIOD_ENABLE,
    PERIOD_SOC,
    PERIOD_POWER,
    PERIOD_START_TIME,
    PERIOD_TIME_END,
    PERIOD_TIME_RATE,
    PERIOD_TIME_START,
    PERIOD_TIME_STOP_SOC,
    POWER_PROTECTION_MODE_TIME_PERIOD,
    PROPERTIES,
)
from .coordinator import HinenDataUpdateCoordinator
from .entity import HinenDeviceEntity
from .utils import extract_property_value


@dataclass(frozen=True, kw_only=True)
class HinenTimeEntityDescription(TimeEntityDescription):
    """Describes Hinen time entity."""

    period_index: int = 0
    property_key: str = ""


# Generate time entity descriptions for CD Period Times (6 periods, each with start and end)
CD_PERIOD_TIME_TYPES: list[HinenTimeEntityDescription] = []
for period_index in range(6):
    CD_PERIOD_TIME_TYPES.extend([
        HinenTimeEntityDescription(
            key=f"cd_period_times_{period_index + 1}_start_time",
            translation_key=f"cd_period_times_{period_index + 1}_start_time",
            entity_category=EntityCategory.CONFIG,
            period_index=period_index,
            property_key=PERIOD_TIME_START,
        ),
        HinenTimeEntityDescription(
            key=f"cd_period_times_{period_index + 1}_end_time",
            translation_key=f"cd_period_times_{period_index + 1}_end_time",
            entity_category=EntityCategory.CONFIG,
            period_index=period_index,
            property_key=PERIOD_TIME_END,
        ),
    ])


# Generate time entity descriptions for Power Protection (6 periods, each with start time only)
POWER_PROTECTION_TIME_TYPES: list[HinenTimeEntityDescription] = []
for period_index in range(6):
    POWER_PROTECTION_TIME_TYPES.append(
        HinenTimeEntityDescription(
            key=f"power_protection_period_{period_index + 1}_start_time",
            translation_key=f"power_protection_period_{period_index + 1}_start_time",
            entity_category=EntityCategory.CONFIG,
            period_index=period_index,
            property_key=PERIOD_START_TIME,
        )
    )


def _minutes_to_time(minutes: int) -> time:
    """Convert minutes (0-1440) to datetime.time."""
    minutes = max(0, min(1440, minutes))
    return time(hour=minutes // 60, minute=minutes % 60)


def _time_to_minutes(t: time) -> int:
    """Convert datetime.time to minutes (0-1440)."""
    return t.hour * 60 + t.minute


def _format_time(minutes: int) -> str:
    """Format minutes as HH:MM string."""
    return _minutes_to_time(minutes).strftime("%H:%M")


def _periods_overlap(start1: int, end1: int, start2: int, end2: int) -> bool:
    """Check if two time periods overlap, supporting cross-day periods.

    A period is cross-day if start > end (e.g., 22:00 - 06:00).
    """
    def normalize_period(start: int, end: int) -> list[tuple[int, int]]:
        """Convert a period to list of (start, end) tuples within 0-1440."""
        if start <= end:
            return [(start, end)]
        else:
            return [(start, 1440), (0, end)]

    segments1 = normalize_period(start1, end1)
    segments2 = normalize_period(start2, end2)

    for s1_start, s1_end in segments1:
        for s2_start, s2_end in segments2:
            if s1_start < s2_end and s1_end > s2_start:
                return True

    return False


class HinenTimeBase(HinenDeviceEntity, TimeEntity):
    """Base class for Hinen time entities with common functionality."""

    entity_description: HinenTimeEntityDescription

    @property
    def native_value(self) -> time | None:
        """Return the current time."""
        if not self.coordinator.data:
            return None

        minutes = self._get_minutes()
        if minutes is None:
            return None
        return _minutes_to_time(minutes)

    def _get_minutes(self) -> int | None:
        """Get current minutes value from coordinator. To be implemented by subclasses."""
        raise NotImplementedError

    async def _update_period_value(
        self,
        minutes: int,
        periods_data_key: str,
        default_period_structure: dict[str, Any],
    ) -> None:
        """Update period value in coordinator and send to device."""
        device_data = self.coordinator.data.get(self._device_id, {})
        property_data = device_data.get(periods_data_key)
        periods = extract_property_value(property_data)

        if periods is None:
            periods = []

        idx = self.entity_description.period_index
        if len(periods) <= idx:
            periods.extend([
                default_period_structure.copy()
                for _ in range(idx - len(periods) + 1)
            ])

        periods[idx][self.entity_description.property_key] = minutes

        await self.hinen_open.set_property(
            periods, self._device_id, PROPERTIES[periods_data_key]
        )

        if isinstance(property_data, dict):
            property_data["value"] = periods
        else:
            device_data[periods_data_key] = {"value": periods, "specs": None}
        self.async_write_ha_state()


class HinenCDPeriodTime(HinenTimeBase):
    """Representation of a Hinen Charge/Discharge Period Time entity."""

    def _get_all_periods(self) -> list[dict]:
        """Get all time periods from coordinator."""
        device_data = self.coordinator.data.get(self._device_id, {})
        cd_period_property = device_data.get(CD_PERIOD_TIMES2)
        cd_period_times = extract_property_value(cd_period_property)
        return cd_period_times if cd_period_times else []

    def _get_minutes(self) -> int | None:
        """Get current minutes from coordinator data."""
        device_data = self.coordinator.data.get(self._device_id, {})
        cd_period_property = device_data.get(CD_PERIOD_TIMES2)
        cd_period_times = extract_property_value(cd_period_property)

        if (
            cd_period_times is None
            or len(cd_period_times) <= self.entity_description.period_index
        ):
            return None

        period_data = cd_period_times[self.entity_description.period_index]
        return period_data.get(self.entity_description.property_key, 0)

    def _validate_time_order(self, new_minutes: int) -> None:
        """Validate that start_time < end_time for the current period."""
        periods = self._get_all_periods()
        idx = self.entity_description.period_index

        if len(periods) <= idx:
            return

        period = periods[idx]
        period_num = idx + 1
        prop_key = self.entity_description.property_key

        if prop_key == PERIOD_TIME_START:
            end_time = period.get(PERIOD_TIME_END, 0)
            if new_minutes >= end_time:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="start_time_equal_or_after_end_time",
                    translation_placeholders={
                        "start_time": _format_time(new_minutes),
                        "end_time": _format_time(end_time),
                        "period": str(period_num),
                    },
                )
        elif prop_key == PERIOD_TIME_END:
            start_time = period.get(PERIOD_TIME_START, 0)
            if new_minutes <= start_time:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="end_time_equal_or_before_start_time",
                    translation_placeholders={
                        "end_time": _format_time(new_minutes),
                        "start_time": _format_time(start_time),
                        "period": str(period_num),
                    },
                )

    def _validate_no_overlap(self, new_minutes: int) -> None:
        """Validate that the period doesn't overlap with other enabled periods."""
        periods = self._get_all_periods()
        current_idx = self.entity_description.period_index

        if len(periods) <= current_idx:
            return

        current_period = dict(periods[current_idx])
        current_period[self.entity_description.property_key] = new_minutes

        prop_start = current_period.get(PERIOD_TIME_START, 0)
        prop_end = current_period.get(PERIOD_TIME_END, 0)

        for other_idx, other_period in enumerate(periods):
            if other_idx == current_idx:
                continue
            if not other_period.get(PERIOD_ENABLE, 0):
                continue

            other_start = other_period.get(PERIOD_TIME_START, 0)
            other_end = other_period.get(PERIOD_TIME_END, 0)

            if other_start == 0 and other_end == 0:
                continue

            if _periods_overlap(prop_start, prop_end, other_start, other_end):
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="period_overlap",
                    translation_placeholders={
                        "period": str(current_idx + 1),
                        "conflict_period": str(other_idx + 1),
                        "period_start": _format_time(prop_start),
                        "period_end": _format_time(prop_end),
                        "conflict_start": _format_time(other_start),
                        "conflict_end": _format_time(other_end),
                    },
                )

    async def async_set_value(self, value: time) -> None:
        """Set the time, converting to minutes for API with validation."""
        minutes = _time_to_minutes(value)

        self._validate_no_overlap(minutes)

        await self._update_period_value(
            minutes,
            CD_PERIOD_TIMES2,
            {
                PERIOD_ENABLE: 0,
                PERIOD_TIME_START: 0,
                PERIOD_TIME_RATE: 0,
                PERIOD_TIME_END: 0,
                PERIOD_TIME_STOP_SOC: 0,
            },
        )


class HinenPowerProtectionTime(HinenTimeBase):
    """Representation of a Hinen Power Keeping (Power Protection) Time entity (start time only)."""

    def _get_minutes(self) -> int | None:
        """Get current start time minutes from coordinator data."""
        device_data = self.coordinator.data.get(self._device_id, {})
        pp_property = device_data.get(POWER_PROTECTION_MODE_TIME_PERIOD)
        pp_periods = extract_property_value(pp_property)

        if (
            pp_periods is None
            or len(pp_periods) <= self.entity_description.period_index
        ):
            return None

        period_data = pp_periods[self.entity_description.period_index]
        return period_data.get(PERIOD_START_TIME, 0)

    async def async_set_value(self, value: time) -> None:
        """Set the start time (no validation)."""
        minutes = _time_to_minutes(value)

        await self._update_period_value(
            minutes,
            POWER_PROTECTION_MODE_TIME_PERIOD,
            {
                PERIOD_AC_ENABLE: 0,
                PERIOD_SOC: 0,
                PERIOD_START_TIME: 0,
                PERIOD_POWER: 0,
            },
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Hinen time entities."""
    coordinator: HinenDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        COORDINATOR
    ]
    hinen_open: HinenOpen = hass.data[DOMAIN][entry.entry_id][AUTH].hinen_open

    entities: list = []
    for device_id in coordinator.data:
        device_data = coordinator.data[device_id]

        if device_data.get(CD_PERIOD_TIMES2) is not None:
            entities.extend(
                HinenCDPeriodTime(coordinator, hinen_open, time_type, device_id)
                for time_type in CD_PERIOD_TIME_TYPES
            )

        if device_data.get(POWER_PROTECTION_MODE_TIME_PERIOD) is not None:
            entities.extend(
                HinenPowerProtectionTime(coordinator, hinen_open, time_type, device_id)
                for time_type in POWER_PROTECTION_TIME_TYPES
            )

    async_add_entities(entities)
