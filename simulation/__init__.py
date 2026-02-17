"""
simulation
----------
Physics / motor simulation package.

Re-exports the two main classes so callers can write::

    from simulation import RotaryAxis, ServoMotor
"""

from simulation.servo_motor import ServoMotor
from simulation.motor import Motor

__all__ = ["ServoMotor", "Motor"]
