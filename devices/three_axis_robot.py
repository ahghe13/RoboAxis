"""
three_axis_robot.py
-------------------
A simple 3-axis robot device using KinematicsChain.

The robot consists of:
  - Base (fixed)
  - Joint 1 (Y-axis rotation, "shoulder")
  - Link 1 (upper arm, 1.0 unit length)
  - Joint 2 (Y-axis rotation, "elbow")
  - Link 2 (forearm, 0.8 unit length)
  - Joint 3 (Y-axis rotation, "wrist")
  - Link 3 (end-effector, 0.3 unit length)
"""
from __future__ import annotations

from typing import Any, Optional

from axis_math import Transform
from component_interface import SceneComponent
from kinematics import Joint, KinematicsChain, Link


class ThreeAxisRobot(SceneComponent):
    """
    A simple 3-DOF serial robot with revolute joints.

    Implements SceneComponent protocol for integration with Scene.

    All joints rotate around the Y-axis. The robot is configured with
    typical arm-like proportions.

    Usage:
        robot = ThreeAxisRobot(name="robot")
        robot.set_joint_angles(shoulder=45.0, elbow=-30.0, wrist=15.0)
        end_effector_tf = robot.get_end_effector_transform()
        definition = robot.get_definition()
        snapshot = robot.snapshot()
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.chain = KinematicsChain()

        # Base link (at origin)
        self.chain.add_link(Link(f"{name}_base", Transform(position=(0.0, 0.0, 0.0))))

        # Shoulder joint (rotates about Y)
        self.chain.add_joint(Joint(f"{name}_shoulder", axis='y'))

        # Upper arm link (1.0 unit along Y)
        self.chain.add_link(Link(f"{name}_upper_arm", Transform(position=(0.0, 1.0, 0.0))))

        # Elbow joint (rotates about Y)
        self.chain.add_joint(Joint(f"{name}_elbow", axis='y'))

        # Forearm link (0.8 unit along Y)
        self.chain.add_link(Link(f"{name}_forearm", Transform(position=(0.0, 0.8, 0.0))))

        # Wrist joint (rotates about Y)
        self.chain.add_joint(Joint(f"{name}_wrist", axis='y'))

        # End-effector link (0.3 unit along Y)
        self.chain.add_link(Link(f"{name}_end_effector", Transform(position=(0.0, 0.3, 0.0))))

    def set_joint_angles(self, shoulder: float = 0.0, elbow: float = 0.0,
                         wrist: float = 0.0) -> None:
        """
        Set the joint angles (in degrees).

        Parameters
        ----------
        shoulder : float  Shoulder joint angle (default: 0.0).
        elbow    : float  Elbow joint angle (default: 0.0).
        wrist    : float  Wrist joint angle (default: 0.0).
        """
        self.chain.set_joint_position(f"{self.name}_shoulder", shoulder)
        self.chain.set_joint_position(f"{self.name}_elbow", elbow)
        self.chain.set_joint_position(f"{self.name}_wrist", wrist)

    def get_joint_angles(self) -> dict[str, float]:
        """Return the current joint angles."""
        return {
            "shoulder": self.chain.get_joint(f"{self.name}_shoulder").position,
            "elbow": self.chain.get_joint(f"{self.name}_elbow").position,
            "wrist": self.chain.get_joint(f"{self.name}_wrist").position,
        }

    def get_end_effector_transform(self) -> Transform:
        """Return the world transform of the end-effector."""
        return self.chain.get_world_transform(f"{self.name}_end_effector")

    def get_definition(self) -> list[dict[str, Any]]:
        """
        Return static robot definition.

        Returns a list of component definitions, one for each link.
        Joints are handled dynamically through transforms and snapshots.

        Returns:
            List of component definitions for all links
        """
        n = self.name
        return [
            # Base link (parent will be set by Scene to robot's parent)
            {"id": f"{n}_base",         "type": "RobotLink",  "model_file": "robot.glb", "model_body": "Body",    "length": 0.0, "parent": None},
            # Shoulder joint
            {"id": f"{n}_shoulder",     "type": "RobotJoint", "axis": "y", "parent": f"{n}_base"},
            # Upper arm link
            {"id": f"{n}_upper_arm",    "type": "RobotLink",  "model_file": "robot.glb", "model_body": "Body001", "length": 1.0, "parent": f"{n}_shoulder"},
            # Elbow joint
            {"id": f"{n}_elbow",        "type": "RobotJoint", "axis": "y", "parent": f"{n}_upper_arm"},
            # Forearm link
            {"id": f"{n}_forearm",      "type": "RobotLink",  "model_file": "robot.glb", "model_body": "Body002", "length": 0.8, "parent": f"{n}_elbow"},
            # Wrist joint
            {"id": f"{n}_wrist",        "type": "RobotJoint", "axis": "y", "parent": f"{n}_forearm"},
            # End-effector link
            {"id": f"{n}_end_effector", "type": "RobotLink",  "model_file": "robot.glb", "model_body": "Body003", "length": 0.3, "parent": f"{n}_wrist"},
        ]

    def get_local_transform_delta(self) -> Optional[Transform]:
        """Return dynamic transform adjustment (none for robot container)."""
        return None

    def snapshot(self) -> dict[str, Any]:
        """
        Return a hierarchical JSON snapshot of the robot.

        Delegates to the underlying KinematicsChain, which returns
        a nested structure that the Scene will inline. Adds "Robot"
        prefix to types so the frontend can use robot-specific models.
        """
        chain_snapshot = self.chain.snapshot()

        # Add "Robot" prefix to all Link/Joint types for frontend model selection
        def prefix_types(node):
            if isinstance(node, dict):
                if node.get("type") == "Link":
                    node["type"] = "RobotLink"
                elif node.get("type") == "Joint":
                    node["type"] = "RobotJoint"

                # Recursively process children
                if "children" in node:
                    for child in node["children"].values():
                        prefix_types(child)

        for root_node in chain_snapshot.values():
            prefix_types(root_node)

        return chain_snapshot


# ── Example Usage ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    robot = ThreeAxisRobot(name="robot")

    print("=== Three-Axis Robot ===")
    print(f"Initial joint angles: {robot.get_joint_angles()}")
    print(f"End-effector transform: {robot.get_end_effector_transform()}")
    print()

    # Get static definition
    definition = robot.get_definition()
    print("=== Robot Definition (Static) ===")
    print(json.dumps(definition, indent=2))
    print()

    # Set some joint angles
    robot.set_joint_angles(shoulder=45.0, elbow=-30.0, wrist=15.0)

    print("=== After Setting Joints ===")
    print(f"Joint angles: {robot.get_joint_angles()}")
    print(f"End-effector transform: {robot.get_end_effector_transform()}")
    print()

    # Generate snapshot
    snapshot = robot.snapshot()
    print("=== Robot Snapshot (JSON) ===")
    print(json.dumps(snapshot, indent=2))