"""
scene.py
--------
Backend representation of the 3D scene.

Tracks which components exist, their spatial transforms, and parent–child
relationships so a kinematic chain can be constructed.

Usage:
    from axis_math import Transform
    from scene import Scene
    from simulation import RotaryAxis

    scene = Scene()
    scene.add("base", RotaryAxis(max_speed=180, acceleration=60),
              transform=Transform(position=(0, 0, 0)))
    scene.add("elbow", RotaryAxis(max_speed=90, acceleration=30),
              parent="base", transform=Transform(position=(0, 1, 0)))
    print(scene.snapshot())
"""
from __future__ import annotations

from typing import Any

from axis_components import AxisBase, AxisRotor
from axis_math import Transform

# Default base height — must match the frontend AxisBase model.
_BASE_HEIGHT = 0.3


# ── Scene ────────────────────────────────────────────────────────────────────

class Scene:
    """Registry of named components forming a kinematic tree."""

    def __init__(self) -> None:
        self._components: dict[str, Any] = {}
        self._transforms: dict[str, Transform] = {}
        self._parents: dict[str, str | None] = {}    # name → parent name
        self._children: dict[str, list[str]] = {}     # name → child names
        self._aliases: dict[str, str] = {}            # user name → rotor node

    def add(self, name: str, component: Any,
            transform: Transform | None = None,
            parent: str | None = None) -> None:
        """Register a component, optionally parented to another.

        If *component* has a ``motor`` attribute (i.e. a RotaryAxis), two
        scene nodes are created automatically: ``{name}_base`` (stationary)
        and ``{name}_rotor`` (child, receives the simulation state).
        Subsequent calls that use ``parent=name`` will attach to the rotor.

        *transform* is the local offset relative to the parent (or world
        origin if no parent).
        """
        # Resolve alias so children attach to the rotor of the parent axis
        parent = self._aliases.get(parent, parent)

        if hasattr(component, "motor"):
            self._add_rotary_axis(name, component, transform, parent)
        else:
            self._add_node(name, component, transform, parent)

    def _add_rotary_axis(self, name: str, axis: Any,
                         transform: Transform | None,
                         parent: str | None) -> None:
        base_name = f"{name}_base"
        rotor_name = f"{name}_rotor"

        self._add_node(base_name, AxisBase(), transform, parent)
        self._add_node(
            rotor_name, AxisRotor(axis),
            Transform(position=(0.0, _BASE_HEIGHT, 0.0)),
            base_name,
        )
        # Alias so parent="axis_1" resolves to the rotor
        self._aliases[name] = rotor_name

    def _add_node(self, name: str, component: Any,
                  transform: Transform | None,
                  parent: str | None) -> None:
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
            self._transforms[child] = self._transforms[name].compose(
                self._transforms[child]
            )
            self._parents[child] = self._parents[name]
            par = self._parents[name]
            if par is not None:
                self._children[par].append(child)

        # Detach from own parent
        par = self._parents.get(name)
        if par is not None and par in self._children:
            self._children[par].remove(name)

        self._transforms.pop(name, None)
        self._parents.pop(name, None)
        self._children.pop(name, None)
        return self._components.pop(name)

    def get(self, name: str) -> Any:
        """Return the component registered as *name*.

        For a RotaryAxis alias, returns the underlying simulation object.
        """
        resolved = self._aliases.get(name, name)
        comp = self._components[resolved]
        if isinstance(comp, AxisRotor):
            return comp.axis
        return comp

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
        """Return a hierarchical JSON snapshot of the scene.

        Components are nested under their parents rather than being flat
        with parent/children references.
        """
        def build_node(name: str) -> dict:
            comp = self._components[name]

            # Let components generate their own snapshot data
            if hasattr(comp, "snapshot"):
                props = comp.snapshot()
                # If the component returns a hierarchical tree (e.g., KinematicsChain),
                # inline it and skip adding scene children
                if isinstance(props, dict) and len(props) == 1:
                    # Single root in snapshot - might be a chain
                    root_key = next(iter(props))
                    root_val = props[root_key]
                    if isinstance(root_val, dict) and "children" in root_val:
                        # Component provided its own hierarchy - use it directly
                        # but apply the scene transform to the root
                        root_val["transform"] = self._transforms[name].to_dict()
                        return root_val

                # Standard component snapshot
                props["name"] = name
                props["transform"] = self._transforms[name].to_dict()
            else:
                # Fallback for components without snapshot()
                props = {"type": type(comp).__name__}
                props["name"] = name
                props["transform"] = self._transforms[name].to_dict()

            # Recursively build scene children (not component's internal children)
            children_names = self._children.get(name, [])
            if children_names:
                props["children"] = {
                    child_name: build_node(child_name)
                    for child_name in children_names
                }

            return props

        # Build tree starting from root nodes (those with no parent)
        root_names = [name for name, parent in self._parents.items() if parent is None]
        return {name: build_node(name) for name in root_names}