"""
scene.py
--------
Backend representation of the 3D scene.

Tracks which components exist, their spatial transforms, and exposes
their properties so the frontend can be kept in sync.

Usage:
    from scene import Scene, Transform
    from simulation import RotaryAxis

    scene = Scene()
    scene.add("axis_1", RotaryAxis(max_speed=180, acceleration=60),
              transform=Transform(position=(1, 0, 0)))
    scene.get("axis_1").set_absolute_position(90)
    print(scene.snapshot())
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Transform:
    """Spatial transform: position, rotation (Euler, degrees), and scale."""
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale:    tuple[float, float, float] = (1.0, 1.0, 1.0)

    def to_dict(self) -> dict[str, list[float]]:
        return {
            "position": list(self.position),
            "rotation": list(self.rotation),
            "scale":    list(self.scale),
        }


class Scene:
    """Registry of named components that make up the simulated scene."""

    def __init__(self) -> None:
        self._components: dict[str, Any] = {}
        self._transforms: dict[str, Transform] = {}

    def add(self, name: str, component: Any,
            transform: Transform | None = None) -> None:
        """Register a component under *name* with an optional transform."""
        if name in self._components:
            raise KeyError(f"Component '{name}' already exists")
        self._components[name] = component
        self._transforms[name] = transform or Transform()

    def remove(self, name: str) -> Any:
        """Remove and return the component registered as *name*."""
        self._transforms.pop(name, None)
        return self._components.pop(name)

    def get(self, name: str) -> Any:
        """Return the component registered as *name*."""
        return self._components[name]

    def get_transform(self, name: str) -> Transform:
        """Return the transform for *name*."""
        return self._transforms[name]

    def set_transform(self, name: str, transform: Transform) -> None:
        """Replace the transform for *name*."""
        if name not in self._components:
            raise KeyError(f"Component '{name}' does not exist")
        self._transforms[name] = transform

    def names(self) -> list[str]:
        """Return all registered component names."""
        return list(self._components.keys())

    def snapshot(self) -> dict[str, dict]:
        """Return a JSON-serialisable snapshot of every component's state."""
        out: dict[str, dict] = {}
        for name, comp in self._components.items():
            props = _component_props(comp)
            props["transform"] = self._transforms[name].to_dict()
            out[name] = props
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