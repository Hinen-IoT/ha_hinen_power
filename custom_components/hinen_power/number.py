"""Support for Hinen Sensors."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from hinen_open_api import HinenOpen
from hinen_open_api.models import SpecsDefinition
from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    AUTH,
    CD_PERIOD_TIMES2,
    CHARGE_STOP_SOC,
    COORDINATOR,
    DOMAIN,
    GRID_FIRST_STOP_SOC,
    LOAD_FIRST_STOP_SOC,
    PERIOD_AC_ENABLE,
    PERIOD_ENABLE,
    PERIOD_POWER,
    PERIOD_SOC,
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

_LOGGER = logging.getLogger(__name__)


def _extract_specs(property_data: Any) -> SpecsDefinition | None:
    """Extract specs from property data."""
    if isinstance(property_data, dict):
        specs = property_data.get("specs")
        if isinstance(specs, SpecsDefinition):
            return specs
    return None


@dataclass(frozen=True, kw_only=True)
class HinenNumberEntityDescription(NumberEntityDescription):
    """Describes Hinen number entity."""


@dataclass(frozen=True, kw_only=True)
class HinenCDPeriodTimesEntityDescription(NumberEntityDescription):
    """Describes Hinen CD Period Times entity."""

    period_index: int = 0
    property_key: str = ""


@dataclass(frozen=True, kw_only=True)
class HinenPowerProtectionNumberEntityDescription(NumberEntityDescription):
    """Describes Hinen Power Protection number entity."""

    period_index: int = 0
    property_key: str = ""


NUMBER_TYPES = [
    HinenNumberEntityDescription(
        key=LOAD_FIRST_STOP_SOC,
        translation_key=LOAD_FIRST_STOP_SOC,
        entity_category=EntityCategory.CONFIG,
        native_min_value=10,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
    ),
    HinenNumberEntityDescription(
        key=CHARGE_STOP_SOC,
        translation_key=CHARGE_STOP_SOC,
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
    ),
    HinenNumberEntityDescription(
        key=GRID_FIRST_STOP_SOC,
        translation_key=GRID_FIRST_STOP_SOC,
        entity_category=EntityCategory.CONFIG,
        native_min_value=10,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
    ),
]

# Generate CD Period Times entity descriptions for 0-6 periods
CD_PERIOD_TIMES_TYPES = []
for period_index in range(6):  # 0-5 periods
    # Period Start
    CD_PERIOD_TIMES_TYPES.append(
        HinenCDPeriodTimesEntityDescription(
            key=f"cd_period_times_{period_index + 1}_start",
            translation_key=f"cd_period_times_{period_index + 1}_start",
            entity_category=EntityCategory.CONFIG,
            native_min_value=0,
            native_max_value=1440,
            native_step=1,
            period_index=period_index,
            property_key=PERIOD_TIME_START,
            native_unit_of_measurement=UnitOfTime.MINUTES,
        )
    )
    # Period Rate
    CD_PERIOD_TIMES_TYPES.append(
        HinenCDPeriodTimesEntityDescription(
            key=f"cd_period_times_{period_index + 1}_rate",
            translation_key=f"cd_period_times_{period_index + 1}_rate",
            entity_category=EntityCategory.CONFIG,
            native_min_value=-100,
            native_max_value=100,
            native_step=1,
            period_index=period_index,
            property_key=PERIOD_TIME_RATE,
            native_unit_of_measurement=PERCENTAGE,
        )
    )
    # Period End
    CD_PERIOD_TIMES_TYPES.append(
        HinenCDPeriodTimesEntityDescription(
            key=f"cd_period_times_{period_index + 1}_end",
            translation_key=f"cd_period_times_{period_index + 1}_end",
            entity_category=EntityCategory.CONFIG,
            native_min_value=0,
            native_max_value=1440,
            native_step=1,
            period_index=period_index,
            property_key=PERIOD_TIME_END,
            native_unit_of_measurement=UnitOfTime.MINUTES,
        )
    )
    # Period Stop SOC
    CD_PERIOD_TIMES_TYPES.append(
        HinenCDPeriodTimesEntityDescription(
            key=f"cd_period_times_{period_index + 1}_stop_soc",
            translation_key=f"cd_period_times_{period_index + 1}_stop_soc",
            entity_category=EntityCategory.CONFIG,
            native_min_value=0,
            native_max_value=100,
            native_step=1,
            period_index=period_index,
            property_key=PERIOD_TIME_STOP_SOC,
            native_unit_of_measurement=PERCENTAGE,
        )
    )


# Generate Power Protection entity descriptions for 0-5 periods
POWER_PROTECTION_TYPES = []
for period_index in range(6):  # 0-5 periods
    # Period SOC
    POWER_PROTECTION_TYPES.append(
        HinenPowerProtectionNumberEntityDescription(
            key=f"power_protection_period_{period_index + 1}_soc",
            translation_key=f"power_protection_period_{period_index + 1}_soc",
            entity_category=EntityCategory.CONFIG,
            native_min_value=0,
            native_max_value=100,
            native_step=1,
            period_index=period_index,
            property_key=PERIOD_SOC,
            native_unit_of_measurement=PERCENTAGE,
        )
    )
    # Period Start Time
    POWER_PROTECTION_TYPES.append(
        HinenPowerProtectionNumberEntityDescription(
            key=f"power_protection_period_{period_index + 1}_start_time",
            translation_key=f"power_protection_period_{period_index + 1}_start_time",
            entity_category=EntityCategory.CONFIG,
            native_min_value=0,
            native_max_value=1440,
            native_step=1,
            period_index=period_index,
            property_key=PERIOD_START_TIME,
            native_unit_of_measurement=UnitOfTime.MINUTES,
        )
    )
    # Period Power
    POWER_PROTECTION_TYPES.append(
        HinenPowerProtectionNumberEntityDescription(
            key=f"power_protection_period_{period_index + 1}_power",
            translation_key=f"power_protection_period_{period_index + 1}_power",
            entity_category=EntityCategory.CONFIG,
            native_min_value=0,
            native_max_value=12000,
            native_step=1,
            period_index=period_index,
            property_key=PERIOD_POWER,
            native_unit_of_measurement=UnitOfPower.WATT,
        )
    )

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Hinen number."""
    coordinator: HinenDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        COORDINATOR
    ]
    hinen_open: HinenOpen = hass.data[DOMAIN][entry.entry_id][AUTH].hinen_open

    entities: list = []
    for device_id in coordinator.data:
        device_data = coordinator.data[device_id]
        for number_type in NUMBER_TYPES:
            if device_data.get(number_type.key) is not None:
                entities.append(
                    HinenNumber(coordinator, hinen_open, number_type, device_id)
                )

        for number_type in CD_PERIOD_TIMES_TYPES:
            if device_data.get(CD_PERIOD_TIMES2) is not None:
                entities.append(
                    HinenCDPeriodTimesNumber(
                        coordinator, hinen_open, number_type, device_id
                    )
                )

        for number_type in POWER_PROTECTION_TYPES:
            pp_data = device_data.get(POWER_PROTECTION_MODE_TIME_PERIOD)
            if pp_data is not None:
                entities.append(
                    HinenPowerProtectionNumber(
                        coordinator, hinen_open, number_type, device_id
                    )
                )

    async_add_entities(entities)


class HinenNumber(HinenDeviceEntity, NumberEntity):
    """Representation of a Hinen load first stop SOC number."""

    entity_description: HinenNumberEntityDescription

    @property
    def available(self) -> bool:
        """Return if the entity is available."""
        return True

    @property
    def native_min_value(self) -> float:
        """Return the minimum value from device specs."""
        device_data = self.coordinator.data.get(self._device_id, {})
        property_data = device_data.get(self.entity_description.key, {})
        specs = _extract_specs(property_data)
        min_val, _ = specs.get_range() if specs else (None, None)
        return min_val if min_val is not None else super().native_min_value

    @property
    def native_max_value(self) -> float:
        """Return the maximum value from device specs."""
        device_data = self.coordinator.data.get(self._device_id, {})
        property_data = device_data.get(self.entity_description.key, {})
        specs = _extract_specs(property_data)
        _, max_val = specs.get_range() if specs else (None, None)
        return max_val if max_val is not None else super().native_max_value

    @property
    def native_step(self) -> float:
        """Return the step value from device specs."""
        device_data = self.coordinator.data.get(self._device_id, {})
        property_data = device_data.get(self.entity_description.key, {})
        specs = _extract_specs(property_data)
        if specs and hasattr(specs, "get"):
            step = specs.get("step")
            if step is not None:
                return float(step)
        return self.entity_description.native_step

    @property
    def native_value(self) -> int | None:
        """Return the current load first stop SOC."""
        if not self.coordinator.data:
            return None
        device_data = self.coordinator.data.get(self._device_id, {})
        property_data = device_data.get(self.entity_description.key)
        return extract_property_value(property_data)

    async def async_set_native_value(self, value: float) -> None:
        """Set the current load first stop SOC."""
        _LOGGER.debug("set native_value: %s", value)
        if value is not None:
            await self.hinen_open.set_property(
                int(value), self._device_id, PROPERTIES[self.entity_description.key]
            )
            # Update coordinator data with new structure
            device_data = self.coordinator.data.get(self._device_id, {})
            current_data = device_data.get(self.entity_description.key)
            if isinstance(current_data, dict):
                current_data["value"] = value
            else:
                device_data[self.entity_description.key] = value
            self.async_write_ha_state()


class HinenCDPeriodTimesNumber(HinenDeviceEntity, NumberEntity):
    """Representation of a Hinen CD Period Times number."""

    entity_description: HinenCDPeriodTimesEntityDescription

    @property
    def available(self) -> bool:
        """Return if the entity is available."""
        return True

    @property
    def native_min_value(self) -> float:
        """Return the minimum value from device specs."""
        specs = self._get_property_specs()
        min_val, _ = specs.get_range() if specs else (None, None)
        return min_val if min_val is not None else super().native_min_value

    @property
    def native_max_value(self) -> float:
        """Return the maximum value from device specs."""
        specs = self._get_property_specs()
        _, max_val = specs.get_range() if specs else (None, None)
        return max_val if max_val is not None else super().native_max_value

    @property
    def native_step(self) -> float:
        """Return the step value from device specs."""
        specs = self._get_property_specs()
        if specs and hasattr(specs, "get"):
            step = specs.get("step")
            if step is not None:
                return float(step)
        return self.entity_description.native_step

    def _get_property_specs(self):
        """Get specs for the property."""
        device_data = self.coordinator.data.get(self._device_id, {})
        property_data = device_data.get(CD_PERIOD_TIMES2)
        return _extract_specs(property_data)

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        if not self.coordinator.data:
            return None

        # Get CDPeriodTimes2 data from coordinator
        device_data = self.coordinator.data.get(self._device_id, {})
        cd_period_property = device_data.get(CD_PERIOD_TIMES2)
        cd_period_times = extract_property_value(cd_period_property)

        if (
            cd_period_times is None
            or len(cd_period_times) <= self.entity_description.period_index
        ):
            return None

        period_data = cd_period_times[self.entity_description.period_index]
        return float(period_data.get(self.entity_description.property_key, 0))

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        _LOGGER.debug("set CD Period Times value: %s", value)
        # Get current CDPeriodTimes2 data
        device_data = self.coordinator.data.get(self._device_id, {})
        cd_period_property = device_data.get(CD_PERIOD_TIMES2)
        cd_period_times = extract_property_value(cd_period_property)

        if cd_period_times is None:
            # Initialize with default values if not exists
            cd_period_times = []

        # Update the specific period and property
        if len(cd_period_times) <= self.entity_description.period_index:
            # Extend the list if needed
            cd_period_times.extend(
                [
                    {
                        PERIOD_ENABLE: 0,
                        PERIOD_TIME_START: 0,
                        PERIOD_TIME_RATE: 0,
                        PERIOD_TIME_END: 0,
                        PERIOD_TIME_STOP_SOC: 0,
                    }
                    for _ in range(
                        self.entity_description.period_index - len(cd_period_times) + 1
                    )
                ]
            )

        period_data = cd_period_times[self.entity_description.period_index]
        period_data[self.entity_description.property_key] = int(value)

        # Send update to device
        await self.hinen_open.set_property(
            cd_period_times, self._device_id, PROPERTIES[CD_PERIOD_TIMES2]
        )

        # Update coordinator data with new structure
        if isinstance(cd_period_property, dict):
            cd_period_property["value"] = cd_period_times
        else:
            device_data[CD_PERIOD_TIMES2] = {"value": cd_period_times, "specs": None}
        self.async_write_ha_state()


class HinenPowerProtectionNumber(HinenDeviceEntity, NumberEntity):
    """Representation of a Hinen Power Protection number."""

    entity_description: HinenPowerProtectionNumberEntityDescription

    @property
    def available(self) -> bool:
        """Return if the entity is available."""
        return True

    @property
    def native_min_value(self) -> float:
        """Return the minimum value."""
        specs = self._get_property_specs()
        min_val, _ = specs.get_range() if specs else (None, None)
        if min_val is not None:
            return min_val
        # Fallback to entity description
        return self.entity_description.native_min_value

    @property
    def native_max_value(self) -> float:
        """Return the maximum value."""
        specs = self._get_property_specs()
        _, max_val = specs.get_range() if specs else (None, None)
        if max_val is not None:
            return max_val
        # Fallback to entity description
        return self.entity_description.native_max_value

    @property
    def native_step(self) -> float:
        """Return the step value from device specs."""
        specs = self._get_property_specs()
        if specs and hasattr(specs, "get"):
            step = specs.get("step")
            if step is not None:
                return float(step)
        # Fallback to entity description
        return self.entity_description.native_step

    def _get_property_specs(self):
        """Get specs for the property."""
        device_data = self.coordinator.data.get(self._device_id, {})
        property_data = device_data.get(POWER_PROTECTION_MODE_TIME_PERIOD)
        outer_specs = _extract_specs(property_data)
        # Find specs for specific property identifier in nested structure
        inner_specs = (
            outer_specs.find_nested_specs(self.entity_description.property_key)
            if outer_specs else None
        )
        return inner_specs

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        if not self.coordinator.data:
            return None

        # Get PowerProtectionModeTimePeriod data from coordinator
        device_data = self.coordinator.data.get(self._device_id, {})
        power_protection_property = device_data.get(POWER_PROTECTION_MODE_TIME_PERIOD)
        power_protection_data = extract_property_value(power_protection_property)

        if (
            power_protection_data is None
            or len(power_protection_data) <= self.entity_description.period_index
        ):
            return None

        period_data = power_protection_data[self.entity_description.period_index]
        return float(period_data.get(self.entity_description.property_key, 0))

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        _LOGGER.debug("set Power Protection value: %s", value)
        # Get current PowerProtectionModeTimePeriod data
        device_data = self.coordinator.data.get(self._device_id, {})
        power_protection_property = device_data.get(POWER_PROTECTION_MODE_TIME_PERIOD)
        power_protection_data = extract_property_value(power_protection_property)

        if power_protection_data is None:
            # Initialize with default values if not exists
            power_protection_data = []

        # Update the specific period and property
        if len(power_protection_data) <= self.entity_description.period_index:
            # Extend the list if needed
            power_protection_data.extend(
                [
                    {
                        PERIOD_SOC: 0,
                        PERIOD_AC_ENABLE: 0,
                        PERIOD_START_TIME: 0,
                        PERIOD_POWER: 0
                    }
                    for _ in range(
                        self.entity_description.period_index
                        - len(power_protection_data)
                        + 1
                    )
                ]
            )

        period_data = power_protection_data[self.entity_description.period_index]
        period_data[self.entity_description.property_key] = int(value)

        # Send update to device
        await self.hinen_open.set_property(
            power_protection_data,
            self._device_id,
            PROPERTIES[POWER_PROTECTION_MODE_TIME_PERIOD],
        )

        # Update coordinator data with new structure
        if isinstance(power_protection_property, dict):
            power_protection_property["value"] = power_protection_data
        else:
            device_data[POWER_PROTECTION_MODE_TIME_PERIOD] = {
                "value": power_protection_data, "specs": None
            }
        self.async_write_ha_state()
