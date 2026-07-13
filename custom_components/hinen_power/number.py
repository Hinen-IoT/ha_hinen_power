"""Support for Hinen Sensors."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from hinen_open_api import HinenOpen
from hinen_open_api.models import SpecsDefinition
from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    AUTH,
    CHARGE_STOP_SOC,
    COORDINATOR,
    DOMAIN,
    GRID_FIRST_STOP_SOC,
    LOAD_FIRST_STOP_SOC,
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
