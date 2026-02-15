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

from typing import Any

from axis_math import Transform


class Joint:
    """
    A single degree of freedom (DoF) in a kinematic chain.

    Joints connect links and introduce articulation. The joint's current
    state (e.g., angle for revolute joints) determines its effective
    transform at runtime.

    Attributes
    ----------
    name      : str        Identifier for this joint.
    axis      : str        Axis of rotation: 'x', 'y', or 'z' (revolute only).
    position  : float      Current joint value (degrees for revolute).
    """

    def __init__(self, name: str, axis: str = 'y') -> None:
        """
        Create a revolute joint rotating about the given axis.

        Parameters
        ----------
        name : str
            Identifier for this joint.
        axis : str
            Rotation axis: 'x', 'y', or 'z' (default: 'y').
        """
        if axis not in ('x', 'y', 'z'):
            raise ValueError(f"Invalid axis '{axis}', must be 'x', 'y', or 'z'")
        self.name = name
        self.axis = axis
        self.position = 0.0

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

    def set_position(self, value: float) -> None:
        """Set the joint position (degrees)."""
        self.position = value

    def snapshot(self) -> dict[str, Any]:
        """Return JSON-serializable state for this joint."""
        return {
            "type": "Joint",
            "name": self.name,
            "axis": self.axis,
            "position": self.position,
        }
