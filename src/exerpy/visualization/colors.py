"""Color utilities for Sankey visualization."""

from __future__ import annotations

# Base colors by fluid identity
_FLUID_BASE: dict[str, str] = {
    "water": "#2196F3",
    "R245FA": "#4CAF50",
    "R134a": "#8BC34A",
    "CH4": "#FF9800",
    "H2": "#E91E63",
    "CO2": "#607D8B",
    "air": "#9E9E9E",
    "flue_gas": "#795548",
    "mixture": "#546E7A",
    "default": "#00BCD4",
}

# Multi-component air identification: subsets of these keys
_AIR_KEYS = {"N2", "O2", "H2O", "CO2", "AR", "Ar", "CH4"}

POWER_COLOR = "#FFC107"
HEAT_COLOR = "#F44336"
ED_COLOR = "#424242"

TERMINAL_COLORS: dict[str, str] = {
    "E_F": "#8D6E63",
    "E_P": "#43A047",
    "E_D": "#E53935",
    "E_L": "#FB8C00",
}

WATERFALL_COLORS: dict[str, str] = {
    "fuel": "#1565C0",
    "destruction": "#D32F2F",
    "loss": "#E65100",
    "product": "#2E7D32",
}

DEFAULT_NODE_COLOR = "#78909C"


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def hex_to_rgba(hex_color: str, alpha: float = 0.6) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    return f"rgba({r},{g},{b},{alpha})"


def shade(hex_color: str, factor: float) -> str:
    """Scale RGB channels by factor (< 1 darkens, > 1 lightens, clamped to 0-255)."""
    r, g, b = _hex_to_rgb(hex_color)
    r = min(255, max(0, int(r * factor)))
    g = min(255, max(0, int(g * factor)))
    b = min(255, max(0, int(b * factor)))
    return f"#{r:02x}{g:02x}{b:02x}"


def fluid_base_color(mass_composition: dict) -> str:
    if not mass_composition:
        return _FLUID_BASE["default"]
    keys = list(mass_composition.keys())
    if len(keys) == 1:
        return _FLUID_BASE.get(keys[0], _FLUID_BASE["default"])
    # Multi-component: classify as air or flue gas if it matches the air-component set
    if set(keys).issubset(_AIR_KEYS):
        co2 = mass_composition.get("CO2", 0) or 0
        return _FLUID_BASE["flue_gas"] if co2 > 0.01 else _FLUID_BASE["air"]
    return _FLUID_BASE["mixture"]


def connection_base_color(conn_data: dict) -> str:
    kind = conn_data.get("kind", "material")
    if kind == "power":
        return POWER_COLOR
    if kind == "heat":
        return HEAT_COLOR
    return fluid_base_color(conn_data.get("mass_composition") or {})
