"""
simulation
----------
Physics / motor simulation package.

Re-exports the two main classes so callers can write::

    from simulation import RotaryAxis, ServoMotor
"""

from simulation.rotary_axis import RotaryAxis
from simulation.servo_motor import ServoMotor

__all__ = ["RotaryAxis", "ServoMotor"]
