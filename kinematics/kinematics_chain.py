"""
kinematics_chain.py
-------------------
KinematicsChain manages a sequence of alternating Links and Joints,
computes forward kinematics, and provides serialization.
"""
from __future__ import annotations

from typing import Any

from axis_math import Transform
from kinematics.joint import Joint
from kinematics.link import Link


class KinematicsChain:
    """
    A serial kinematic chain composed of alternating Links and Joints.

    The chain represents a sequence: Link → Joint → Link → Joint → ...
    Forward kinematics compute the world transform of each element by
    composing transforms from the base.

    Usage:
        chain = KinematicsChain()
        chain.add_link(Link("base", Transform(position=(0, 0, 0))))
        chain.add_joint(Joint("shoulder", axis='y'))
        chain.add_link(Link("upper_arm", Transform(position=(0, 1, 0))))
        chain.add_joint(Joint("elbow", axis='y'))
        chain.add_link(Link("forearm", Transform(position=(0, 1, 0))))

        chain.set_joint_position("shoulder", 45.0)
        chain.set_joint_position("elbow", -30.0)
        world_tf = chain.get_world_transform("forearm")
    """

    def __init__(self) -> None:
        self._elements: list[Link | Joint] = []
        self._name_to_index: dict[str, int] = {}

    def add_link(self, link: Link) -> None:
        """Add a Link to the end of the chain."""
        if link.name in self._name_to_index:
            raise ValueError(f"Element '{link.name}' already exists in the chain")
        self._name_to_index[link.name] = len(self._elements)
        self._elements.append(link)

    def add_joint(self, joint: Joint) -> None:
        """Add a Joint to the end of the chain."""
        if joint.name in self._name_to_index:
            raise ValueError(f"Element '{joint.name}' already exists in the chain")
        self._name_to_index[joint.name] = len(self._elements)
        self._elements.append(joint)

    def get_joint(self, name: str) -> Joint:
        """Return the joint with the given name."""
        idx = self._name_to_index.get(name)
        if idx is None:
            raise KeyError(f"Joint '{name}' not found in chain")
        elem = self._elements[idx]
        if not isinstance(elem, Joint):
            raise TypeError(f"'{name}' is a Link, not a Joint")
        return elem

    def get_link(self, name: str) -> Link:
        """Return the link with the given name."""
        idx = self._name_to_index.get(name)
        if idx is None:
            raise KeyError(f"Link '{name}' not found in chain")
        elem = self._elements[idx]
        if not isinstance(elem, Link):
            raise TypeError(f"'{name}' is a Joint, not a Link")
        return elem

    def set_joint_position(self, name: str, value: float) -> None:
        """Set the position of a joint by name."""
        self.get_joint(name).set_position(value)

    def get_world_transform(self, name: str) -> Transform:
        """
        Compute the world transform of the element with the given name.

        Composes all transforms from the base of the chain up to and
        including the named element.
        """
        idx = self._name_to_index.get(name)
        if idx is None:
            raise KeyError(f"Element '{name}' not found in chain")

        result = Transform()
        for i in range(idx + 1):
            elem = self._elements[i]
            if isinstance(elem, Link):
                result = result.compose(elem.transform)
            elif isinstance(elem, Joint):
                result = result.compose(elem.get_transform())
        return result

    def elements(self) -> list[Link | Joint]:
        """Return all elements in the chain (read-only)."""
        return list(self._elements)

    def snapshot(self) -> dict[str, Any]:
        """
        Return a hierarchical JSON snapshot of the chain.

        Each element is nested under its predecessor, forming a linear
        hierarchy: base → joint → link → joint → ...
        """
        if not self._elements:
            return {}

        def build_node(index: int) -> dict[str, Any]:
            elem = self._elements[index]
            node = elem.snapshot()

            # Add transform
            if isinstance(elem, Link):
                node["transform"] = elem.transform.to_dict()
            elif isinstance(elem, Joint):
                node["transform"] = elem.get_transform().to_dict()

            # Recursively add next element as a child
            if index + 1 < len(self._elements):
                next_elem = self._elements[index + 1]
                node["children"] = {next_elem.name: build_node(index + 1)}

            return node

        # Start from the first element (base link)
        first = self._elements[0]
        return {first.name: build_node(0)}


# ── Tester ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    # Build a simple 2-joint arm
    chain = KinematicsChain()
    chain.add_link(Link("base", Transform(position=(0.0, 0.0, 0.0))))
    chain.add_joint(Joint("shoulder", axis='y'))
    chain.add_link(Link("upper_arm", Transform(position=(0.0, 1.0, 0.0))))
    chain.add_joint(Joint("elbow", axis='y'))
    chain.add_link(Link("forearm", Transform(position=(0.0, 1.0, 0.0))))

    print("=== Initial State (all joints at 0°) ===")
    print(f"Shoulder world transform: {chain.get_world_transform('shoulder')}")
    print(f"Elbow world transform:    {chain.get_world_transform('elbow')}")
    print(f"Forearm world transform:  {chain.get_world_transform('forearm')}")
    print()

    # Set joint positions
    chain.set_joint_position("shoulder", 45.0)
    chain.set_joint_position("elbow", -30.0)

    print("=== After Setting Joints (shoulder=45°, elbow=-30°) ===")
    print(f"Shoulder world transform: {chain.get_world_transform('shoulder')}")
    print(f"Elbow world transform:    {chain.get_world_transform('elbow')}")
    print(f"Forearm world transform:  {chain.get_world_transform('forearm')}")
    print()

    # Generate snapshot
    snapshot = chain.snapshot()
    print("=== Hierarchical Snapshot (JSON) ===")
    print(json.dumps(snapshot, indent=2))
    print()

    # Test element access
    print("=== Element Access ===")
    shoulder = chain.get_joint("shoulder")
    print(f"Shoulder joint: {shoulder.name}, axis={shoulder.axis}, position={shoulder.position}°")
    upper_arm = chain.get_link("upper_arm")
    print(f"Upper arm link: {upper_arm.name}, transform={upper_arm.transform}")
    print()

    # Show all elements
    print("=== All Elements ===")
    for i, elem in enumerate(chain.elements()):
        elem_type = "Link" if isinstance(elem, Link) else "Joint"
        print(f"{i}: {elem_type} '{elem.name}'")