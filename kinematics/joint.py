"""
joint.py
-------------
Kinematic chain primitives: Link and Joint.

A kinematic chain is composed of alternating Links and Joints:
    Link → Joint → Link → Joint → ...

Each Link represents a rigid body segment with a fixed transform.
Each Joint represents a degree of freedom (DoF) with variable state.
"""
from __future__ import annotations

from typing import Any, Optional

from axis_math import Transform
from scene.scene_component import SceneComponent
from simulation.servo_motor import ServoMotor


class Joint(SceneComponent):
    """
    A single degree of freedom (DoF) in a kinematic chain.

    Joints connect links and introduce articulation. The joint's current
    angle (read from the internal ServoMotor) determines its effective
    transform at runtime.

    Attributes
    ----------
    name      : str        Identifier for this joint.
    axis      : str        Axis of rotation: 'x', 'y', or 'z' (revolute only).
    position  : float      Current joint angle in degrees (read from motor).
    """

    def get_component_type(self) -> str:
        return "joint"

    def __init__(self, name: str, axis: str = 'y',
                 max_speed: float = 180.0, acceleration: float = 60.0) -> None:
        """
        Create a revolute joint rotating about the given axis.

        Parameters
        ----------
        name         : str    Identifier for this joint.
        axis         : str    Rotation axis: 'x', 'y', or 'z' (default: 'y').
        max_speed    : float  Top speed in °/s (default: 180).
        acceleration : float  Ramp rate in °/s² (default: 60).
        """
        super().__init__()
        if axis not in ('x', 'y', 'z'):
            raise ValueError(f"Invalid axis '{axis}', must be 'x', 'y', or 'z'")
        self.name = name
        self.axis = axis
        self._motor = ServoMotor(max_speed=max_speed, acceleration=acceleration)

    @property
    def position(self) -> float:
        """Current joint angle in degrees, normalised to [0, 360)."""
        return self._motor.position

    @property
    def speed(self) -> float:
        """Instantaneous joint speed in degrees per second."""
        return self._motor.speed

    @property
    def is_moving(self) -> bool:
        """True while the joint is in motion."""
        return self._motor.is_moving

    @property
    def motor(self) -> ServoMotor:
        """Direct access to the underlying ServoMotor."""
        return self._motor

    def get_transform(self) -> Transform:
        """
        Return the current transform for this joint based on its state.

        For a revolute joint, this is a rotation about the joint's axis
        by the current position (in degrees).
        """
        rotation = {
            'x': (self.position, 0.0, 0.0),
            'y': (0.0, self.position, 0.0),
            'z': (0.0, 0.0, self.position),
        }[self.axis]
        return Transform(rotation=rotation)

    def get_state(self, parent_transform: Optional[Transform] = None) -> dict[str, Any]:
        """Return the joint's world transform plus live motor state."""
        state = super().get_state(parent_transform)
        state["position"]     = self.position
        state["speed"]        = self.speed
        state["acceleration"] = self._motor._motor._acceleration
        state["is_moving"]    = self.is_moving
        return state

    def set_position(self, value: float) -> None:
        """Command the joint to move to *value* degrees (non-blocking)."""
        self._motor.set_absolute_position(value)
