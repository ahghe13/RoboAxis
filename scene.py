"""
scene.py
--------
Backend representation of the 3D scene.

Tracks which components exist, their spatial transforms, and parent–child
relationships so a kinematic chain can be constructed.

Usage:
    from axis_math import Transform
    from scene import Scene

    scene = Scene()
    scene.add("robot", robot, transform=Transform(position=(0, 0, 0)))
    scene.add("tool", tool, parent="robot", transform=Transform(position=(0, 1, 0)))
    print(scene.snapshot())
"""
from __future__ import annotations

from typing import Any

from axis_math import Transform
from component_interface import SceneComponent


# ── Scene ────────────────────────────────────────────────────────────────────

class Scene:
    """Registry of named components forming a kinematic tree."""

    def __init__(self) -> None:
        self._components: dict[str, SceneComponent] = {}
        self._transforms: dict[str, Transform] = {}
        self._parents: dict[str, str | None] = {}    # name → parent name
        self._children: dict[str, list[str]] = {}    # name → child names

    def add(self, name: str, component: SceneComponent,
            transform: Transform | None = None,
            parent: str | None = None) -> None:
        """Register a component, optionally parented to another.

        *transform* is the local offset relative to the parent (or world
        origin if no parent).
        """
        self._add_node(name, component, transform, parent)

    def _add_node(self, name: str, component: SceneComponent,
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

    def remove(self, name: str) -> SceneComponent:
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

    def get(self, name: str) -> SceneComponent:
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

    def static_scene_definition(self) -> dict[str, Any]:
        """Return a static scene definition describing the component hierarchy.

        This describes the structure of the scene without dynamic state (transforms,
        positions, etc.). Useful for initializing the frontend or understanding
        the scene graph topology.

        Returns:
            {
                "type": "static_scene_definition",
                "components": [
                    {
                        "id": "base",
                        "type": "Link",
                        "parent": null,
                        "model_node": "Base"
                    },
                    ...
                ]
            }
        """
        components = []

        def add_component_def(name: str) -> None:
            """Add component definition and recurse through children."""
            comp = self._components[name]
            parent = self._parents.get(name)

            # Get component's static definitions (may be multiple for complex components)
            component_defs = comp.get_definition()

            # Add scene-level metadata to each definition
            for component_def in component_defs:
                # Set id only if not already provided by the component
                if "id" not in component_def:
                    component_def["id"] = name
                # Set parent only if not already defined by the component
                # (for multi-component definitions, only the root gets the scene parent)
                if "parent" not in component_def or component_def["parent"] is None:
                    component_def["parent"] = parent
                components.append(component_def)

            # Process children
            for child_name in self._children.get(name, []):
                add_component_def(child_name)

        # Process all root nodes
        for name in [n for n, p in self._parents.items() if p is None]:
            add_component_def(name)

        return {
            "type": "static_scene_definition",
            "components": components,
        }

    def snapshot(self) -> dict[str, Any]:
        """Return a state update snapshot of the scene.

        Returns:
            {
                "type": "state_update",
                "components": [
                    {"id": "component_name", "matrix": [16 numbers]},
                    ...
                ]
            }
        """
        components: list[dict[str, Any]] = []

        def add_component(name: str, parent_world_tf: Transform) -> None:
            """Add a component and its descendants to the components list."""
            comp = self._components[name]
            local_tf = self._transforms[name]

            # Apply dynamic transform adjustment if component provides one
            delta = comp.get_local_transform_delta()
            if delta is not None:
                local_tf = local_tf.compose(delta)

            world_tf = parent_world_tf.compose(local_tf)

            # Get component snapshot
            props = comp.snapshot()

            # If the component returns a hierarchical tree (e.g., KinematicsChain),
            # flatten it into the components list
            if isinstance(props, dict) and len(props) == 1:
                root_key = next(iter(props))
                root_val = props[root_key]
                if isinstance(root_val, dict) and "children" in root_val:
                    # Component is a chain - flatten it
                    _flatten_chain(root_val, world_tf)
                    # Process scene children (if any)
                    for child_name in self._children.get(name, []):
                        add_component(child_name, world_tf)
                    return

            # Standard component snapshot - just id and matrix
            components.append({
                "id": name,
                "matrix": world_tf.to_matrix_list(),
            })

            # Process scene children
            for child_name in self._children.get(name, []):
                add_component(child_name, world_tf)

        def _flatten_chain(node: dict, parent_tf: Transform) -> None:
            """Recursively flatten a kinematic chain into the components list."""
            name = node.get("name")
            if not name:
                return

            # Get local transform
            if "transform" in node:
                local_dict = node["transform"]
                local_tf = Transform(
                    position=tuple(local_dict["position"]),
                    rotation=tuple(local_dict["rotation"]),
                    scale=tuple(local_dict["scale"]),
                )
            else:
                local_tf = Transform()

            # Compute world transform
            world_tf = parent_tf.compose(local_tf)

            # Add to components list - just id and matrix
            components.append({
                "id": name,
                "matrix": world_tf.to_matrix_list(),
            })

            # Process children
            if "children" in node:
                for child_node in node["children"].values():
                    _flatten_chain(child_node, world_tf)

        # Process all root nodes
        identity = Transform()
        for name in [n for n, p in self._parents.items() if p is None]:
            add_component(name, identity)

        return {
            "type": "state_update",
            "components": components,
        }