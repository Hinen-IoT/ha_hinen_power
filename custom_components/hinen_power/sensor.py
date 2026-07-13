"""Support for Hinen Sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from hinen_open_api import HinenOpen
from hinen_open_api.enum import DeviceAlertStatus, DeviceStatus
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import (
    ATTR_ALERT_STATUS,
    ATTR_STATUS,
    AUTH,
    BATTERY_POWER,
    CD_PERIOD_TIMES2,
    CD_PERIOD_WEEK_SUPPORT,
    COORDINATOR,
    CUMULATIVE_CONSUMPTION,
    CUMULATIVE_ENERGY_PURCHASED,
    CUMULATIVE_GRID_FEED_IN,
    CUMULATIVE_PRODUCTION_ACTIVE,
    DOMAIN,
    GENERATION_POWER,
    GRID_TOTAL_POWER,
    POWER_PROTECTION_HELPER_SENSOR_KEY,
    POWER_PROTECTION_MODE_TIME_PERIOD,
    SOC,
    TOTAL_CHARGING_ENERGY,
    TOTAL_DISCHARGING_ENERGY,
    TOTAL_LOAD_POWER,
    VPP_TYPE,
    VPP_TYPE_NONE,
    VPP_TYPE_OPTIONS,
)
from .coordinator import HinenDataUpdateCoordinator
from .entity import HinenDeviceEntity
from .utils import extract_property_specs, extract_property_value


def _is_property_available(device_detail: dict, key: str) -> bool:
    """Check if property is available."""
    if key not in device_detail:
        return False

    property_data = device_detail[key]
    if isinstance(property_data, dict):
        return property_data.get("value") is not None
    return property_data is not None


@dataclass(frozen=True, kw_only=True)
class HinenSensorEntityDescription(SensorEntityDescription):
    """Describes Hinen sensor entity."""

    available_fn: Callable[[Any], bool]
    value_fn: Callable[[Any], StateType]


SENSOR_TYPES = [
    HinenSensorEntityDescription(
        key=ATTR_STATUS,
        translation_key=ATTR_STATUS,
        available_fn=lambda d: _is_property_available(d, ATTR_STATUS),
        value_fn=lambda device_detail: DeviceStatus.from_value(
            device_detail[ATTR_STATUS]
        ).name.lower(),
    ),
    HinenSensorEntityDescription(
        key=ATTR_ALERT_STATUS,
        translation_key=ATTR_ALERT_STATUS,
        available_fn=lambda d: _is_property_available(d, ATTR_ALERT_STATUS),
        value_fn=lambda device_detail: DeviceAlertStatus.from_value(
            device_detail[ATTR_ALERT_STATUS]
        ).name.lower(),
    ),
    # Power sensors
    HinenSensorEntityDescription(
        key=GENERATION_POWER,
        translation_key=GENERATION_POWER,
        available_fn=lambda d: _is_property_available(d, GENERATION_POWER),
        value_fn=lambda d: extract_property_value(d.get(GENERATION_POWER)),
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    HinenSensorEntityDescription(
        key=TOTAL_LOAD_POWER,
        translation_key=TOTAL_LOAD_POWER,
        available_fn=lambda d: _is_property_available(d, TOTAL_LOAD_POWER),
        value_fn=lambda d: extract_property_value(d.get(TOTAL_LOAD_POWER)),
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    HinenSensorEntityDescription(
        key=BATTERY_POWER,
        translation_key=BATTERY_POWER,
        available_fn=lambda d: _is_property_available(d, BATTERY_POWER),
        value_fn=lambda d: extract_property_value(d.get(BATTERY_POWER)),
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    HinenSensorEntityDescription(
        key=GRID_TOTAL_POWER,
        translation_key=GRID_TOTAL_POWER,
        available_fn=lambda d: _is_property_available(d, GRID_TOTAL_POWER),
        value_fn=lambda d: extract_property_value(d.get(GRID_TOTAL_POWER)),
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Battery charge level sensor
    HinenSensorEntityDescription(
        key=SOC,
        translation_key=SOC,
        available_fn=lambda d: _is_property_available(d, SOC),
        value_fn=lambda d: extract_property_value(d.get(SOC)),
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    HinenSensorEntityDescription(
        key=CUMULATIVE_CONSUMPTION,
        translation_key=CUMULATIVE_CONSUMPTION,
        available_fn=lambda device_detail: device_detail[CUMULATIVE_CONSUMPTION]
        is not None,
        value_fn=lambda d: extract_property_value(d.get(CUMULATIVE_CONSUMPTION)),
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
    ),
    HinenSensorEntityDescription(
        key=CUMULATIVE_PRODUCTION_ACTIVE,
        translation_key=CUMULATIVE_PRODUCTION_ACTIVE,
        available_fn=lambda device_detail: device_detail[CUMULATIVE_PRODUCTION_ACTIVE]
        is not None,
        value_fn=lambda d: extract_property_value(d.get(CUMULATIVE_PRODUCTION_ACTIVE)),
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
    ),
    HinenSensorEntityDescription(
        key=CUMULATIVE_GRID_FEED_IN,
        translation_key=CUMULATIVE_GRID_FEED_IN,
        available_fn=lambda device_detail: device_detail[CUMULATIVE_GRID_FEED_IN]
        is not None,
        value_fn=lambda d: extract_property_value(d.get(CUMULATIVE_GRID_FEED_IN)),
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
    ),
    HinenSensorEntityDescription(
        key=TOTAL_CHARGING_ENERGY,
        translation_key=TOTAL_CHARGING_ENERGY,
        available_fn=lambda device_detail: device_detail[TOTAL_CHARGING_ENERGY]
        is not None,
        value_fn=lambda d: extract_property_value(d.get(TOTAL_CHARGING_ENERGY)),
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
    ),
    HinenSensorEntityDescription(
        key=TOTAL_DISCHARGING_ENERGY,
        translation_key=TOTAL_DISCHARGING_ENERGY,
        available_fn=lambda device_detail: device_detail[TOTAL_DISCHARGING_ENERGY]
        is not None,
        value_fn=lambda d: extract_property_value(d.get(TOTAL_DISCHARGING_ENERGY)),
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
    ),
    HinenSensorEntityDescription(
        key=CUMULATIVE_ENERGY_PURCHASED,
        translation_key=CUMULATIVE_ENERGY_PURCHASED,
        available_fn=lambda device_detail: device_detail[CUMULATIVE_ENERGY_PURCHASED]
        is not None,
        value_fn=lambda d: extract_property_value(d.get(CUMULATIVE_ENERGY_PURCHASED)),
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
    ),
    HinenSensorEntityDescription(
        key=VPP_TYPE,
        translation_key=VPP_TYPE,
        available_fn=lambda d: _is_property_available(d, VPP_TYPE),
        value_fn=lambda device_detail: VPP_TYPE_OPTIONS.get(
            extract_property_value(device_detail.get(VPP_TYPE)),
            VPP_TYPE_OPTIONS[VPP_TYPE_NONE]
        ),
    ),
]


@dataclass(frozen=True, kw_only=True)
class HinenPeriodHelperDescription(SensorEntityDescription):
    """Describes Hinen Period Helper sensor."""


PERIOD_HELPER_TYPE = HinenPeriodHelperDescription(
    key="cd_period_times2_config",
    translation_key="cd_period_times2_config",
    entity_category=EntityCategory.DIAGNOSTIC,
)


@dataclass(frozen=True, kw_only=True)
class HinenPowerProtectionHelperDescription(SensorEntityDescription):
    """Describes Hinen Power Protection Helper sensor."""


POWER_PROTECTION_HELPER_TYPE = HinenPowerProtectionHelperDescription(
    key=POWER_PROTECTION_HELPER_SENSOR_KEY,
    translation_key=POWER_PROTECTION_HELPER_SENSOR_KEY,
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Hinen sensor."""
    coordinator: HinenDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        COORDINATOR
    ]
    hinen_open: HinenOpen = hass.data[DOMAIN][entry.entry_id][AUTH].hinen_open

    entities: list = []
    for device_id in coordinator.data:
        device_data = coordinator.data[device_id]
        for sensor_type in SENSOR_TYPES:
            if device_data.get(sensor_type.key) is not None:
                entities.append(
                    HinenSensor(coordinator, hinen_open, sensor_type, device_id)
                )

        # Helper sensor exposing full CDPeriodTimes2 array
        if device_data.get(CD_PERIOD_TIMES2) is not None:
            entities.append(
                HinenPeriodHelperSensor(
                    coordinator, hinen_open, PERIOD_HELPER_TYPE, device_id
                )
            )
        
        # Helper sensor exposing full PowerProtectionModeTimePeriod array
        if device_data.get(POWER_PROTECTION_MODE_TIME_PERIOD) is not None:
            entities.append(
                HinenPowerProtectionHelperSensor(
                    coordinator, hinen_open, POWER_PROTECTION_HELPER_TYPE, device_id
                )
            )

    async_add_entities(entities)


class HinenSensor(HinenDeviceEntity, SensorEntity):
    """Representation of a Hinen sensor."""

    entity_description: HinenSensorEntityDescription

    @property
    def available(self) -> bool:
        """Return if the entity is available."""
        return super().available

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        return self.entity_description.value_fn(self.coordinator.data[self._device_id])


class HinenPeriodHelperSensor(HinenDeviceEntity, SensorEntity):
    """Expose CDPeriodTimes2 full array as attributes for custom cards."""

    entity_description: HinenPeriodHelperDescription

    _attr_should_poll = False

    @property
    def native_value(self) -> str:
        """Return fixed value."""
        return "configured"

    @property
    def extra_state_attributes(self) -> dict:
        """Expose full CDPeriodTimes2 array."""
        device_data = self.coordinator.data.get(self._device_id, {})
        cd_period = device_data.get(CD_PERIOD_TIMES2)
        periods = extract_property_value(cd_period) or []
        
        # Check if device supports week configuration
        week_support_prop = device_data.get(CD_PERIOD_WEEK_SUPPORT)
        week_support = 0
        if week_support_prop:
            week_support_val = extract_property_value(week_support_prop)
            if week_support_val is not None:
                # 如果是布尔值，True=1, False=0；如果是数字，直接用
                week_support = 1 if week_support_val is True else (int(week_support_val) if str(week_support_val).isdigit() else 0)
        
        return {
            "cd_period_times2": periods,
            "cd_period_week_support": week_support,
            "api_device_id": self._device_id,
            "field_specs": extract_property_specs(cd_period),
        }


class HinenPowerProtectionHelperSensor(HinenDeviceEntity, SensorEntity):
    """Expose PowerProtectionModeTimePeriod full array as attributes for custom cards."""

    entity_description: HinenPowerProtectionHelperDescription

    _attr_should_poll = False

    @property
    def native_value(self) -> str:
        """Return fixed value."""
        return "configured"

    @property
    def extra_state_attributes(self) -> dict:
        """Expose full PowerProtectionModeTimePeriod array."""
        device_data = self.coordinator.data.get(self._device_id, {})
        power_protection = device_data.get(POWER_PROTECTION_MODE_TIME_PERIOD)
        periods = extract_property_value(power_protection) or []
        
        return {
            "power_protection_mode_time_period": periods,
            "api_device_id": self._device_id,
            "field_specs": extract_property_specs(power_protection),
        }
