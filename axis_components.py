"""
axis_components.py
------------------
Scene-level wrappers for the two parts of a rotary axis:
AxisBase (stationary) and AxisRotor (rotating, wraps the simulation).
"""
from __future__ import annotations

from typing import Any


class AxisBase:
    """Stationary base of a rotary axis (scene node marker)."""
    pass


class AxisRotor:
    """Rotating part of a rotary axis — wraps the simulation component."""

    def __init__(self, axis: Any) -> None:
        self.axis = axis

    @property
    def position(self) -> float:
        return self.axis.position

    @property
    def speed(self) -> float:
        return self.axis.speed

    @property
    def is_moving(self) -> bool:
        return self.axis.is_moving

    @property
    def motor(self) -> Any:
        return self.axis.motor