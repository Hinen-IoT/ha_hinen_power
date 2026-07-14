"""Utility functions for Hinen Power integration."""

from __future__ import annotations

from typing import Any


def extract_property_value(property_data: Any) -> Any:
    """Extract value from property data.

    Handles coordinator data structure: {"value": actual_value, "specs": ...}
    """
    if isinstance(property_data, dict) and "value" in property_data:
        return property_data["value"]
    return property_data


def extract_property_specs(property_data: Any) -> dict[str, dict]:
    """Extract field specs from property data as identifier → specs map.

    Property data structure:
        {
          "value": [...],
          "specs": SpecsDefinition or dict  # from coordinator
        }

    For array-type specs with struct fields:
        {
          "specs": [
            {"identifier": "PeriodSOC", "specs": {"min": 10, "max": 100}, ...},
            ...
          ],
          "arrayType": "struct"
        }

    Returns a flat dict: {"PeriodSOC": {"min": 10, "max": 100}, ...}
    """
    if not isinstance(property_data, dict):
        return {}
    
    # Get specs from property_data
    outer_specs = property_data.get("specs")
    if outer_specs is None:
        return {}
    
    # Convert pydantic model to dict if needed
    if hasattr(outer_specs, "model_dump"):
        outer_specs = outer_specs.model_dump()
    elif hasattr(outer_specs, "dict") and not isinstance(outer_specs, dict):
        outer_specs = outer_specs.dict()  # type: ignore[attr-defined]
    
    if not isinstance(outer_specs, dict):
        return {}
    
    # For array-type specs, items are in "specs" field
    specs_list = outer_specs.get("specs")
    if not isinstance(specs_list, list):
        return {}
    
    result: dict[str, dict] = {}
    for item in specs_list:
        if not isinstance(item, dict):
            continue
        identifier = item.get("identifier")
        if identifier:
            result[identifier] = item.get("specs") or {}
    return result


def _enum_text_value(property_data: Any) -> str | None:
    """Look up current enum index in property's enumList and return the text field."""
    if not isinstance(property_data, dict):
        return None

    current_value = property_data.get("value")
    specs = property_data.get("specs")
    if current_value is None or specs is None:
        return None

    # Convert pydantic model to dict if needed
    if hasattr(specs, "model_dump"):
        specs_dict = specs.model_dump()
    elif hasattr(specs, "dict") and not isinstance(specs, dict):
        specs_dict = specs.dict()  # type: ignore[attr-defined]
    elif isinstance(specs, dict):
        specs_dict = specs
    else:
        return None

    enum_list = specs_dict.get("enumList")
    if not isinstance(enum_list, list):
        return None

    try:
        current_int = int(current_value)
    except (ValueError, TypeError):
        return None

    for entry in enum_list:
        if isinstance(entry, dict) and entry.get("value") == current_int:
            text_value = entry.get("text")
            if text_value is not None:
                return str(text_value)

    return None


def get_dynamic_lower_limit(bat_settable_data: Any) -> float | None:
    """Get dynamic lower limit from BatSettableMinSocLevel data."""
    text = _enum_text_value(bat_settable_data)
    if text is None:
        return None
    try:
        return float(text)
    except (ValueError, TypeError):
        return None


def resolve_enum_percentage_value(device_detail: dict[str, Any], key: str) -> int | None:
    """Resolve enum property to its text value as int."""
    text = _enum_text_value(device_detail.get(key))
    if text is None:
        return None
    try:
        return int(text)
    except (ValueError, TypeError):
        return None
