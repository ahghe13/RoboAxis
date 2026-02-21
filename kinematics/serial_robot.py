"""
serial_robot.py
---------------
SerialRobot represents a serial-chain robot arm as a SceneComponent node.
It is constructed from a robot descriptor dict (or JSON file).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Union

from axis_math.axis_math import Transform
from kinematics.joint import Joint
from scene.scene_component import SceneComponent


def _parse_transform(d: dict) -> Transform:
    pos = d.get("position", [0.0, 0.0, 0.0])
    rot = d.get("rotation", [0.0, 0.0, 0.0])
    scl = d.get("scale",    [1.0, 1.0, 1.0])
    return Transform(
        position=(pos[0], pos[1], pos[2]),
        rotation=(rot[0], rot[1], rot[2]),
        scale=   (scl[0], scl[1], scl[2]),
    )


class SerialRobot(SceneComponent):
    """A serial-chain robot arm constructed from a descriptor.

    Joints are chained as children: SerialRobot → joint_1 → joint_2 → …
    The flat ``joints`` list provides direct indexed access to every joint.

    Attributes
    ----------
    name       : str          Name from the descriptor.
    joints     : list[Joint]  Ordered list of all joints, root to tip.
    tcp_offset : Transform    Fixed offset from the last joint frame to the TCP.
    """

    def __init__(self, descriptor: dict) -> None:
        super().__init__()
        self.name: str = descriptor.get("name", "serial_robot")

        if "transform" in descriptor:
            self.transform = _parse_transform(descriptor["transform"])

        self.joints: list[Joint] = []
        self._tcp_offset: Transform = Transform()

        parent: SceneComponent = self
        for i, jd in enumerate(descriptor.get("joints", []), start=1):
            joint = Joint(
                name=f"joint{i}",
                axis=jd.get("axis", "y"),
                max_speed=jd.get("max_speed", 180.0),
                acceleration=jd.get("acceleration", 60.0),
            )
            if "transform" in jd:
                joint.transform = _parse_transform(jd["transform"])
            if "cad_file" in jd:
                joint.cad_file = jd["cad_file"]
            if "cad_body" in jd:
                joint.cad_body = jd["cad_body"]
            parent.add_child(joint)
            self.joints.append(joint)
            parent = joint
            joint.transform_locked = True

        if "tcp_offset" in descriptor:
            self._tcp_offset = _parse_transform(descriptor["tcp_offset"])

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> SerialRobot:
        """Load a robot descriptor from a JSON file and construct a SerialRobot."""
        with open(path) as f:
            return cls(json.load(f))

    def get_component_type(self) -> str:
        return "serial_robot"

    # ── Joint transforms (fixed local offsets) ────────────────────────────────

    def set_joint_transform(self, index: int, transform: Transform) -> None:
        """Set the fixed local offset transform of joint at *index*."""
        self.joints[index].transform = transform

    def get_joint_transform(self, index: int) -> Transform:
        """Return the fixed local offset transform of joint at *index*."""
        return self.joints[index].transform

    # ── Joint angles ──────────────────────────────────────────────────────────

    def set_joint_angle(self, index: int, angle: float) -> None:
        """Command joint at *index* to move to *angle* degrees (non-blocking)."""
        self.joints[index].set_position(angle)

    def get_joint_angle(self, index: int) -> float:
        """Return the current angle of joint at *index* in degrees [0, 360)."""
        return self.joints[index].position

    # ── Jog ───────────────────────────────────────────────────────────────────

    def jog_cw(self, index: int) -> None:
        """Jog joint at *index* clockwise at its configured speed until stopped."""
        self.joints[index].motor.jog_cw()

    def jog_ccw(self, index: int) -> None:
        """Jog joint at *index* counter-clockwise at its configured speed until stopped."""
        self.joints[index].motor.jog_ccw()

    def jog_stop(self, index: int) -> None:
        """Stop an active jog on joint at *index* with a deceleration ramp."""
        self.joints[index].motor.jog_stop()

    # ── TCP offset ────────────────────────────────────────────────────────────

    @property
    def tcp_offset(self) -> Transform:
        """Fixed transform from the last joint frame to the TCP."""
        return self._tcp_offset

    @tcp_offset.setter
    def tcp_offset(self, value: Transform) -> None:
        self._tcp_offset = value

    # ── Forward kinematics ────────────────────────────────────────────────────

    def get_tcp_transform(self) -> Transform:
        """Compute the world transform of the TCP.

        Composes the robot's own transform, then for each joint its fixed
        local offset followed by its current rotation, and finally the TCP
        offset.
        """
        result = self.transform
        for joint in self.joints:
            result = result.compose(joint.transform)
            result = result.compose(joint.get_transform())
        return result.compose(self._tcp_offset)