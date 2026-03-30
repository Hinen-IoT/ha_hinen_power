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