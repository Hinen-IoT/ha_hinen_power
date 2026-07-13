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