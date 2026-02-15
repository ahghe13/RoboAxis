"""
axis_math.py
------------
Spatial transform and Euler rotation utilities.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


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

    def to_matrix(self) -> np.ndarray:
        """Convert to a 4x4 transformation matrix.

        Returns a homogeneous transformation matrix that combines
        rotation, scale, and translation.
        """
        # Build rotation matrix (3x3)
        R = euler_to_matrix(self.rotation)

        # Apply scale to rotation matrix
        S = np.diag(self.scale)
        RS = R @ S

        # Build 4x4 homogeneous matrix
        mat = np.eye(4)
        mat[:3, :3] = RS
        mat[:3, 3] = self.position

        return mat

    def to_matrix_list(self) -> list[list[float]]:
        """Convert to a 4x4 matrix as nested lists (JSON-serializable)."""
        return self.to_matrix().tolist()

    def compose(self, child: Transform) -> Transform:
        """Return the world transform of *child* given *self* as the parent.

        Applies parent's scale and rotation to the child's local offset,
        then adds the parent's position.  Rotations are composed via
        rotation matrices (Euler XYZ order).
        """
        parent_mat = euler_to_matrix(self.rotation)

        # Scale the child offset by parent scale, then rotate by parent rotation
        scaled = np.array(child.position) * np.array(self.scale)
        world_pos = tuple(np.array(self.position) + parent_mat @ scaled)

        # Compose rotations via matrices
        child_mat = euler_to_matrix(child.rotation)
        world_rot = matrix_to_euler(parent_mat @ child_mat)

        # Compose scales
        world_scale = tuple(np.array(self.scale) * np.array(child.scale))

        return Transform(position=world_pos, rotation=world_rot, scale=world_scale)


def euler_to_matrix(euler: tuple[float, float, float]) -> np.ndarray:
    """3x3 rotation matrix from Euler XYZ angles in degrees."""
    rx, ry, rz = np.radians(euler)
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    return np.array([
        [cy * cz,  sx * sy * cz - cx * sz,  cx * sy * cz + sx * sz],
        [cy * sz,  sx * sy * sz + cx * cz,  cx * sy * sz - sx * cz],
        [-sy,      sx * cy,                 cx * cy],
    ])


def matrix_to_euler(m: np.ndarray) -> tuple[float, float, float]:
    """Extract Euler XYZ angles (degrees) from a 3x3 rotation matrix."""
    sy = -m[2, 0]
    if abs(sy) < 1.0 - 1e-6:
        ry = math.asin(sy)
        rx = math.atan2(m[2, 1], m[2, 2])
        rz = math.atan2(m[1, 0], m[0, 0])
    else:
        ry = math.copysign(math.pi / 2, sy)
        rx = math.atan2(-m[1, 2], m[1, 1])
        rz = 0.0
    return (math.degrees(rx), math.degrees(ry), math.degrees(rz))