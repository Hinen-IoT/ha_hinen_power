"""Support for Hinen switches."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from hinen_open_api import HinenOpen
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import AUTH, CD_PERIOD_TIMES2, COORDINATOR, DOMAIN, PROPERTIES, POWER_PROTECTION_MODE_TIME_PERIOD
from .coordinator import HinenDataUpdateCoordinator
from .entity import HinenDeviceEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=False)
class HinenCDPeriodEnableEntityDescription(SwitchEntityDescription):
    """Describes Hinen CD Period Enable entity."""

    period_index: int = 0


@dataclass(frozen=True, kw_only=False)
class HinenPowerProtectionACEnableEntityDescription(SwitchEntityDescription):
    """Describes Hinen Power Protection AC Enable entity."""

    period_index: int = 0


# Generate CD Period Enable entity descriptions for 0-6 periods
CD_PERIOD_ENABLE_TYPES = [
    HinenCDPeriodEnableEntityDescription(
        key=f"cd_period_times_{period_index + 1}_enable",
        translation_key=f"cd_period_times_{period_index + 1}_enable",
        entity_category=EntityCategory.CONFIG,
        period_index=period_index,
    )
    for period_index in range(6)  # 0-6 periods
]


# Generate Power Protection AC Enable entity descriptions for 0-5 periods
POWER_PROTECTION_AC_ENABLE_TYPES = [
    HinenPowerProtectionACEnableEntityDescription(
        key=f"power_protection_period_{period_index + 1}_ac_enable",
        translation_key=f"power_protection_period_{period_index + 1}_ac_enable",
        entity_category=EntityCategory.CONFIG,
        period_index=period_index,
    )
    for period_index in range(6)  # 0-5 periods
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Hinen CD Period Enable switches and Power Protection AC Enable switches."""
    coordinator: HinenDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        COORDINATOR
    ]
    hinen_open: HinenOpen = hass.data[DOMAIN][entry.entry_id][AUTH].hinen_open

    entities: list = []
    for device_id in coordinator.data:
        device_data = coordinator.data[device_id]
        for switch_type in CD_PERIOD_ENABLE_TYPES:
            if device_data.get(CD_PERIOD_TIMES2) is not None:
                entities.append(HinenCDPeriodEnableSwitch(coordinator, hinen_open, switch_type, device_id))

        for switch_type in POWER_PROTECTION_AC_ENABLE_TYPES:
            if device_data.get(POWER_PROTECTION_MODE_TIME_PERIOD) is not None:
                entities.append(HinenPowerProtectionACEnableSwitch(coordinator, hinen_open, switch_type, device_id))

    async_add_entities(entities)


class HinenCDPeriodEnableSwitch(HinenDeviceEntity, SwitchEntity):
    """Representation of a Hinen CD Period Enable switch."""

    entity_description: HinenCDPeriodEnableEntityDescription

    @property
    def available(self) -> bool:
        """Return if the entity is available."""
        return True

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        if not self.coordinator.data:
            return False

        # Get CDPeriodTimes2 data from coordinator
        cd_period_times = self.coordinator.data[self._device_id][CD_PERIOD_TIMES2]
        if (
            cd_period_times is None
            or len(cd_period_times) <= self.entity_description.period_index
        ):
            return False

        period_data = cd_period_times[self.entity_description.period_index]
        return bool(period_data.get("periodEnable", 0))

    async def async_turn_on(self, **kwargs: Any) -> None: # pylint: disable=unused-argument
        """Turn the switch on."""
        await self._set_enable_value(True)

    async def async_turn_off(self, **kwargs: Any) -> None: # pylint: disable=unused-argument
        """Turn the switch off."""
        await self._set_enable_value(False)

    async def _set_enable_value(self, enabled: bool) -> None:
        """Set the enable value."""
        _LOGGER.debug(
            "Setting CD Period Enable to: %s for period: %s",
            enabled,
            self.entity_description.period_index,
        )

        # Get current CDPeriodTimes2 data
        cd_period_times = self.coordinator.data[self._device_id][CD_PERIOD_TIMES2]
        if cd_period_times is None:
            # Initialize with default values if not exists
            cd_period_times = []

        # Update the specific period
        if len(cd_period_times) <= self.entity_description.period_index:
            # Extend the list if needed
            cd_period_times.extend(
                [
                    {
                        "periodEnable": 0,
                        "periodTimeStart": 0,
                        "periodTimeRate": 0,
                        "periodTimeEnd": 0,
                        "periodTimeStopSoc": 0,
                    }
                    for _ in range(
                        self.entity_description.period_index - len(cd_period_times) + 1
                    )
                ]
            )

        period_data = cd_period_times[self.entity_description.period_index]
        period_data["periodEnable"] = 1 if enabled else 0

        # Send update to device
        await self.hinen_open.set_property(
            cd_period_times, self._device_id, PROPERTIES[CD_PERIOD_TIMES2]
        )

        # Update coordinator data
        self.coordinator.data[self._device_id][CD_PERIOD_TIMES2] = cd_period_times

        self.async_write_ha_state()


class HinenPowerProtectionACEnableSwitch(HinenDeviceEntity, SwitchEntity):
    """Representation of a Hinen Power Protection AC Enable switch."""

    entity_description: HinenPowerProtectionACEnableEntityDescription

    @property
    def available(self) -> bool:
        """Return if the entity is available."""
        return True

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        if not self.coordinator.data:
            return False

        # Get PowerProtectionModeTimePeriod data from coordinator
        power_protection_data = self.coordinator.data[self._device_id][POWER_PROTECTION_MODE_TIME_PERIOD]
        if (
            power_protection_data is None
            or len(power_protection_data) <= self.entity_description.period_index
        ):
            return False

        period_data = power_protection_data[self.entity_description.period_index]
        return bool(period_data.get("PeriodACEnable", 0))

    async def async_turn_on(self, **kwargs: Any) -> None: # pylint: disable=unused-argument
        """Turn the switch on."""
        await self._set_enable_value(True)

    async def async_turn_off(self, **kwargs: Any) -> None: # pylint: disable=unused-argument
        """Turn the switch off."""
        await self._set_enable_value(False)

    async def _set_enable_value(self, enabled: bool) -> None:
        """Set the enable value."""
        _LOGGER.debug(
            "Setting Power Protection AC Enable to: %s for period: %s",
            enabled,
            self.entity_description.period_index,
        )

        # Get current PowerProtectionModeTimePeriod data
        power_protection_data = self.coordinator.data[self._device_id][POWER_PROTECTION_MODE_TIME_PERIOD]
        if power_protection_data is None:
            # Initialize with default values if not exists
            power_protection_data = []

        # Update the specific period
        if len(power_protection_data) <= self.entity_description.period_index:
            # Extend the list if needed
            power_protection_data.extend(
                [
                    {
                        "PeriodSOC": 0,
                        "PeriodACEnable": 0,
                        "PeriodStartTime": 0,
                        "PeriodPower": 0
                    }
                    for _ in range(
                        self.entity_description.period_index - len(power_protection_data) + 1
                    )
                ]
            )

        period_data = power_protection_data[self.entity_description.period_index]
        period_data["PeriodACEnable"] = 1 if enabled else 0

        # Send update to device
        await self.hinen_open.set_property(
            power_protection_data, self._device_id, PROPERTIES[POWER_PROTECTION_MODE_TIME_PERIOD]
        )

        # Update coordinator data
        self.coordinator.data[self._device_id][POWER_PROTECTION_MODE_TIME_PERIOD] = power_protection_data

        self.async_write_ha_state()