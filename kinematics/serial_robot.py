"""
serial_robot.py
---------------
SerialRobot represents a serial-chain robot arm as a SceneComponent node.
"""
from __future__ import annotations

from kinematics.joint import Joint
from scene.scene_component import SceneComponent


class SerialRobot(SceneComponent):
    """A serial-chain robot arm in the scene graph.

    Joints are chained as children: SerialRobot → joint_1 → joint_2 → …
    The flat ``joints`` list provides direct indexed access to every joint.

    Attributes
    ----------
    joints : list[Joint]  Ordered list of all joints, root to tip.
    """

    def __init__(self, num_joints: int) -> None:
        super().__init__()
        self.joints: list[Joint] = []

        parent: SceneComponent = self
        for i in range(num_joints):
            joint = Joint(name=f"joint_{i + 1}")
            parent.add_child(joint)
            self.joints.append(joint)
            parent = joint

    def get_component_type(self) -> str:
        return "serial_robot"