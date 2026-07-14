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
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    AUTH,
    BAT_CHG_MAX_SOC,
    BAT_SETTABLE_MIN_SOC_LEVEL,
    CHARGE_STOP_SOC,
    COORDINATOR,
    DOMAIN,
    GRID_FIRST_STOP_SOC,
    LOAD_FIRST_STOP_SOC,
    PROPERTIES,
)
from .coordinator import HinenDataUpdateCoordinator
from .entity import HinenDeviceEntity
from .utils import extract_property_value, get_dynamic_lower_limit

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
    HinenNumberEntityDescription(
        key=BAT_CHG_MAX_SOC,
        translation_key=BAT_CHG_MAX_SOC,
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
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

    def _verify_value_in_range(self, value: float) -> None:
        """Skip framework range check for SOC entities."""
        key = self.entity_description.key
        if key in (LOAD_FIRST_STOP_SOC, BAT_CHG_MAX_SOC):
            return
        super()._verify_value_in_range(value)

    @property
    def native_min_value(self) -> float:
        """Return the minimum value.

        For LoadFirstStopSOC and BatChgMaxSoc, use BatSettableMinSocLevel's
        dynamic lower limit (from enumList mapping). Fall back to own specs if
        BatSettableMinSocLevel is not available.
        """
        device_data = self.coordinator.data.get(self._device_id, {})
        entity_key = self.entity_description.key

        if entity_key in (LOAD_FIRST_STOP_SOC, BAT_CHG_MAX_SOC):
            bat_settable_data = device_data.get(BAT_SETTABLE_MIN_SOC_LEVEL)
            dynamic_limit = get_dynamic_lower_limit(bat_settable_data)
            if dynamic_limit is not None:
                return dynamic_limit

        property_data = device_data.get(entity_key, {})
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
        entity_key = self.entity_description.key
        device_data = self.coordinator.data.get(self._device_id, {})

        # For SOC cross-entity entities, validate device-specs range
        # (bypassed in _verify_value_in_range so our custom error fires first).
        if entity_key in (LOAD_FIRST_STOP_SOC, BAT_CHG_MAX_SOC):
            property_data = device_data.get(entity_key, {})
            specs = _extract_specs(property_data)
            if specs:
                spec_min, spec_max = specs.get_range()
                if (spec_min is not None and value < spec_min) or (
                    spec_max is not None and value > spec_max
                ):
                    raise ServiceValidationError(
                        translation_domain=DOMAIN,
                        translation_key="soc_out_of_spec_range",
                        translation_placeholders={
                            "entity": entity_key,
                            "value": str(int(value)),
                            "min": str(int(spec_min) if spec_min is not None else "0"),
                            "max": str(int(spec_max) if spec_max is not None else "100"),
                        },
                    )

        # Cross-entity validation: LOAD_FIRST_STOP_SOC <= BAT_CHG_MAX_SOC
        if entity_key == LOAD_FIRST_STOP_SOC:
            charge_max_data = device_data.get(BAT_CHG_MAX_SOC)
            charge_max_val = extract_property_value(charge_max_data)
            if charge_max_val is not None and value > charge_max_val:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="discharge_min_exceeds_charge_max",
                    translation_placeholders={
                        "discharge_min": str(int(value)),
                        "charge_max": str(int(charge_max_val)),
                    },
                )
        elif entity_key == BAT_CHG_MAX_SOC:
            discharge_min_data = device_data.get(LOAD_FIRST_STOP_SOC)
            discharge_min_val = extract_property_value(discharge_min_data)
            if discharge_min_val is not None and value < discharge_min_val:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="discharge_min_exceeds_charge_max",
                    translation_placeholders={
                        "discharge_min": str(int(discharge_min_val)),
                        "charge_max": str(int(value)),
                    },
                )

        if value is not None:
            await self.hinen_open.set_property(
                int(value), self._device_id, PROPERTIES[entity_key]
            )
            # Update coordinator data with new structure
            current_data = device_data.get(entity_key)
            if isinstance(current_data, dict):
                current_data["value"] = value
            else:
                device_data[entity_key] = value
            self.async_write_ha_state()
