"""
scene.py
--------
Backend representation of the 3D scene.

Tracks which components exist, their spatial transforms, and parent–child
relationships so a kinematic chain can be constructed.

Usage:
    from scene import Scene, Transform
    from simulation import RotaryAxis

    scene = Scene()
    scene.add("base", RotaryAxis(max_speed=180, acceleration=60),
              transform=Transform(position=(0, 0, 0)))
    scene.add("elbow", RotaryAxis(max_speed=90, acceleration=30),
              parent="base", transform=Transform(position=(0, 1, 0)))
    print(scene.snapshot())
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


# ── Transform ────────────────────────────────────────────────────────────────

@dataclass
class Transform:
    """Spatial transform: position, rotation (Euler XYZ, degrees), and scale."""
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale:    tuple[float, float, float] = (1.0, 1.0, 1.0)

    def to_dict(self) -> dict[str, list[float]]:
        return {
            "position": list(self.position),
            "rotation": list(self.rotation),
            "scale":    list(self.scale),
        }

    def compose(self, child: Transform) -> Transform:
        """Return the world transform of *child* given *self* as the parent.

        Applies parent's scale and rotation to the child's local offset,
        then adds the parent's position.  Rotations are composed via
        rotation matrices (Euler XYZ order).
        """
        # Scale the child offset by parent scale
        sx, sy, sz = self.scale
        cx, cy, cz = child.position
        scaled = (cx * sx, cy * sy, cz * sz)

        # Rotate scaled offset by parent rotation
        rotated = _rotate_vec(self.rotation, scaled)

        # World position = parent pos + rotated offset
        px, py, pz = self.position
        world_pos = (px + rotated[0], py + rotated[1], pz + rotated[2])

        # Compose rotations via matrices
        parent_mat = _euler_to_matrix(self.rotation)
        child_mat = _euler_to_matrix(child.rotation)
        combined = _mat_mul(parent_mat, child_mat)
        world_rot = _matrix_to_euler(combined)

        # Compose scales
        csx, csy, csz = child.scale
        world_scale = (sx * csx, sy * csy, sz * csz)

        return Transform(position=world_pos, rotation=world_rot, scale=world_scale)


# ── Rotation helpers (Euler XYZ, degrees) ────────────────────────────────────

def _euler_to_matrix(euler: tuple[float, float, float]) -> list[list[float]]:
    """3x3 rotation matrix from Euler XYZ angles in degrees."""
    rx, ry, rz = (math.radians(a) for a in euler)
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    return [
        [cy * cz,  sx * sy * cz - cx * sz,  cx * sy * cz + sx * sz],
        [cy * sz,  sx * sy * sz + cx * cz,  cx * sy * sz - sx * cz],
        [-sy,      sx * cy,                 cx * cy],
    ]


def _matrix_to_euler(m: list[list[float]]) -> tuple[float, float, float]:
    """Extract Euler XYZ angles (degrees) from a 3x3 rotation matrix."""
    sy = -m[2][0]
    if abs(sy) < 1.0 - 1e-6:
        ry = math.asin(sy)
        rx = math.atan2(m[2][1], m[2][2])
        rz = math.atan2(m[1][0], m[0][0])
    else:
        ry = math.copysign(math.pi / 2, sy)
        rx = math.atan2(-m[1][2], m[1][1])
        rz = 0.0
    return (math.degrees(rx), math.degrees(ry), math.degrees(rz))


def _mat_mul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    """Multiply two 3x3 matrices."""
    return [
        [sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)]
        for i in range(3)
    ]


def _rotate_vec(euler: tuple[float, float, float],
                vec: tuple[float, float, float]) -> tuple[float, float, float]:
    """Rotate a vector by Euler XYZ angles (degrees)."""
    m = _euler_to_matrix(euler)
    x, y, z = vec
    return (
        m[0][0] * x + m[0][1] * y + m[0][2] * z,
        m[1][0] * x + m[1][1] * y + m[1][2] * z,
        m[2][0] * x + m[2][1] * y + m[2][2] * z,
    )


# ── Scene ────────────────────────────────────────────────────────────────────

class Scene:
    """Registry of named components forming a kinematic tree."""

    def __init__(self) -> None:
        self._components: dict[str, Any] = {}
        self._transforms: dict[str, Transform] = {}
        self._parents: dict[str, str | None] = {}    # name → parent name
        self._children: dict[str, list[str]] = {}     # name → child names

    def add(self, name: str, component: Any,
            transform: Transform | None = None,
            parent: str | None = None) -> None:
        """Register a component, optionally parented to another.

        *transform* is the local offset relative to the parent (or world
        origin if no parent).
        """
        if name in self._components:
            raise KeyError(f"Component '{name}' already exists")
        if parent is not None and parent not in self._components:
            raise KeyError(f"Parent '{parent}' does not exist")

        self._components[name] = component
        self._transforms[name] = transform or Transform()
        self._parents[name] = parent
        self._children.setdefault(name, [])

        if parent is not None:
            self._children[parent].append(name)

    def remove(self, name: str) -> Any:
        """Remove a component and reparent its children to the scene root."""
        # Reparent children
        for child in self._children.get(name, []):
            # Bake the removed node's transform into each child
            self._transforms[child] = self._transforms[name].compose(
                self._transforms[child]
            )
            self._parents[child] = self._parents[name]
            parent = self._parents[name]
            if parent is not None:
                self._children[parent].append(child)

        # Detach from own parent
        parent = self._parents.get(name)
        if parent is not None and parent in self._children:
            self._children[parent].remove(name)

        self._transforms.pop(name, None)
        self._parents.pop(name, None)
        self._children.pop(name, None)
        return self._components.pop(name)

    def get(self, name: str) -> Any:
        """Return the component registered as *name*."""
        return self._components[name]

    def get_transform(self, name: str) -> Transform:
        """Return the local transform for *name*."""
        return self._transforms[name]

    def set_transform(self, name: str, transform: Transform) -> None:
        """Replace the local transform for *name*."""
        if name not in self._components:
            raise KeyError(f"Component '{name}' does not exist")
        self._transforms[name] = transform

    def get_parent(self, name: str) -> str | None:
        """Return the parent name, or None if at the root."""
        return self._parents[name]

    def get_children(self, name: str) -> list[str]:
        """Return the names of direct children."""
        return list(self._children.get(name, []))

    def world_transform(self, name: str) -> Transform:
        """Compute the world transform by composing up the kinematic chain."""
        chain: list[str] = []
        current: str | None = name
        while current is not None:
            chain.append(current)
            current = self._parents[current]

        # Compose from root down
        result = Transform()
        for n in reversed(chain):
            result = result.compose(self._transforms[n])
        return result

    def names(self) -> list[str]:
        """Return all registered component names."""
        return list(self._components.keys())

    def snapshot(self) -> dict[str, dict]:
        """Return a JSON-serialisable snapshot of every component's state."""
        out: dict[str, dict] = {}
        for name, comp in self._components.items():
            props = _component_props(comp)
            props["transform"] = self._transforms[name].to_dict()
            props["parent"] = self._parents[name]
            props["children"] = list(self._children.get(name, []))
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