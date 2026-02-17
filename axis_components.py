"""
axis_components.py
------------------
Scene-level wrappers for the two parts of a rotary axis:
AxisBase (stationary) and AxisRotor (rotating, wraps the simulation).
"""
from __future__ import annotations

from typing import Any, Optional

from axis_math import Transform


class AxisBase:
    """Stationary base of a rotary axis (scene node marker).

    Implements SceneComponent protocol.
    """

    def get_definition(self) -> list[dict[str, Any]]:
        """Return static component definition."""
        return [{
            "type": "AxisBase",
        }]

    def get_local_transform_delta(self) -> Optional[Transform]:
        """Return dynamic transform adjustment (none for static base)."""
        return None

    def snapshot(self) -> dict[str, Any]:
        """Return JSON-serializable state for this component."""
        return {"type": "AxisBase"}


class AxisRotor:
    """Rotating part of a rotary axis — wraps the simulation component.

    Implements SceneComponent protocol.
    """

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

    def get_definition(self) -> list[dict[str, Any]]:
        """Return static component definition."""
        return [{
            "type": "AxisRotor",
            "max_speed": self.axis.motor._max_speed,
            "acceleration": self.axis.motor._acceleration,
        }]

    def get_local_transform_delta(self) -> Optional[Transform]:
        """Return dynamic rotation transform based on current position."""
        return Transform(rotation=(0.0, self.position, 0.0))

    def snapshot(self) -> dict[str, Any]:
        """Return JSON-serializable state for this component."""
        return {
            "type": "AxisRotor",
            "position": self.axis.position,
            "speed": self.axis.speed,
            "is_moving": self.axis.is_moving,
            "max_speed": self.axis.motor._max_speed,
            "acceleration": self.axis.motor._acceleration,
            "state": self.axis.motor.state,
        }