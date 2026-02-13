"""
scene.py
--------
Backend representation of the 3D scene.

Tracks which components exist and exposes their properties so the
frontend can be kept in sync.

Usage:
    from scene import Scene
    from rotary_axis import RotaryAxis

    scene = Scene()
    scene.add("axis_1", RotaryAxis(max_speed=180, acceleration=60))
    scene.get("axis_1").set_absolute_position(90)
    print(scene.snapshot())
"""
from __future__ import annotations

from typing import Any


class Scene:
    """Registry of named components that make up the simulated scene."""

    def __init__(self) -> None:
        self._components: dict[str, Any] = {}

    def add(self, name: str, component: Any) -> None:
        """Register a component under *name*."""
        if name in self._components:
            raise KeyError(f"Component '{name}' already exists")
        self._components[name] = component

    def remove(self, name: str) -> Any:
        """Remove and return the component registered as *name*."""
        return self._components.pop(name)

    def get(self, name: str) -> Any:
        """Return the component registered as *name*."""
        return self._components[name]

    def names(self) -> list[str]:
        """Return all registered component names."""
        return list(self._components.keys())

    def snapshot(self) -> dict[str, dict]:
        """Return a JSON-serialisable snapshot of every component's state."""
        out: dict[str, dict] = {}
        for name, comp in self._components.items():
            out[name] = _component_props(comp)
        return out


def _component_props(comp: Any) -> dict:
    """Extract a property dict from a component using duck-typed attributes."""
    props: dict[str, Any] = {"type": type(comp).__name__}
    if hasattr(comp, "position"):
        props["position"] = comp.position
    if hasattr(comp, "speed"):
        props["speed"] = comp.speed
    if hasattr(comp, "is_moving"):
        props["is_moving"] = comp.is_moving
    if hasattr(comp, "motor"):
        motor = comp.motor
        props["max_speed"] = motor._max_speed
        props["acceleration"] = motor._acceleration
        props["state"] = motor.state
    return props