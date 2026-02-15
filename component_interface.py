"""
component_interface.py
----------------------
Protocol interface for scene components.

Components can implement this interface to provide:
  - get_definition(): Static structure/configuration (type, children, etc.)
  - snapshot(): Dynamic state (positions, velocities, etc.)
  - get_local_transform_delta(): Dynamic transform adjustments
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Protocol

if TYPE_CHECKING:
    from axis_math import Transform


class SceneComponent(Protocol):
    """Protocol for components that can be added to a Scene.

    Components implementing this interface can provide both static
    structure information and dynamic state snapshots.
    """

    def get_definition(self) -> list[dict[str, Any]]:
        """Return static component definitions.

        This describes the component's structure, type, and configuration
        without any dynamic state. Components may contain multiple
        sub-components (e.g., a robot with multiple links and joints).

        Returns:
            List of component definition dicts. Simple components return
            a single-element list, complex components return multiple.
        """
        ...

    def snapshot(self) -> dict[str, Any]:
        """Return current dynamic state.

        This captures the component's current state including positions,
        velocities, transforms, and any other time-varying properties.

        Returns:
            State snapshot dict with current values
        """
        ...

    def get_local_transform_delta(self) -> Optional["Transform"]:
        """Return dynamic transform adjustment to apply to local transform.

        For components with dynamic state that affects their transform
        (e.g., AxisRotor rotation), this returns the transform delta
        to compose with the static local transform.

        Returns:
            Transform delta, or None if no dynamic adjustment needed
        """
        ...