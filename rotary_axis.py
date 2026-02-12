"""
rotary_axis.py
--------------
High-level rotary axis controller built on top of ServoMotor.

Usage:
    from rotary_axis import RotaryAxis

    axis = RotaryAxis(max_speed=180.0, acceleration=60.0)
    axis.set_absolute_position(270.0)
    axis.wait_for_move()
    print(axis.position)   # ~270.0
"""
from __future__ import annotations

import threading
import time

from servo_motor import ServoMotor


class RotaryAxis:
    """
    High-level rotary axis controller built on top of a ServoMotor.

    Adds goal-position moves (absolute & relative), runtime speed/acceleration
    tuning, and open-ended jog in either direction.

    Coordinate system
    -----------------
    Positions are expressed in degrees.  ``position`` is always normalised to
    [0, 360).  Moves always travel the *shortest angular path* unless a
    direction is forced by a jog command.

    Parameters
    ----------
    max_speed    : float  Top speed in °/s (default 180).
    acceleration : float  Ramp rate in °/s² (default 60).
    tick_rate    : float  Simulation frequency forwarded to ServoMotor (default 200 Hz).
    """

    # How close (degrees) is "close enough" to declare arrival
    _POSITION_TOLERANCE: float = 0.05

    def __init__(
        self,
        max_speed: float = 180.0,
        acceleration: float = 60.0,
        tick_rate: float = 200.0,
    ) -> None:
        self._motor = ServoMotor(
            max_speed=max_speed,
            acceleration=acceleration,
            tick_rate=tick_rate,
        )

        # Move-tracking state (protected by _axis_lock)
        self._axis_lock = threading.Lock()
        self._goal: float | None = None        # target in raw (unbounded) degrees
        self._jogging: bool = False            # True while an open-ended jog is active
        self._move_thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_speed(self, max_speed: float) -> None:
        """Set the cruising speed in degrees per second."""
        if max_speed <= 0:
            raise ValueError("max_speed must be positive.")
        with self._motor._lock:
            self._motor._max_speed = float(max_speed)

    def set_acceleration(self, acceleration: float) -> None:
        """Set the acceleration / deceleration ramp rate in degrees per second squared."""
        if acceleration <= 0:
            raise ValueError("acceleration must be positive.")
        with self._motor._lock:
            self._motor._acceleration = float(acceleration)

    # ------------------------------------------------------------------
    # Goal-position moves
    # ------------------------------------------------------------------

    def set_absolute_position(self, target_deg: float) -> None:
        """
        Move to an absolute angle (degrees).

        The axis always travels the *shortest* arc to the target.
        The call returns immediately; the move runs on a background thread.
        Use ``wait_for_move()`` to block until arrival.
        """
        current = self._motor.position   # [0, 360)
        target  = target_deg % 360.0

        # Shortest-path delta in (-180, +180]
        delta = (target - current + 180.0) % 360.0 - 180.0
        self._start_move(delta)

    def set_relative_position(self, delta_deg: float) -> None:
        """
        Move by a relative angle (positive = CW, negative = CCW).

        The call returns immediately; use ``wait_for_move()`` to block.
        """
        self._start_move(delta_deg)

    def wait_for_move(self, timeout: float | None = None) -> bool:
        """
        Block until the current move completes (or timeout expires).

        Returns True if the move finished, False if it timed out.
        """
        with self._axis_lock:
            thread = self._move_thread
        if thread is None:
            return True
        thread.join(timeout=timeout)
        return not thread.is_alive()

    # ------------------------------------------------------------------
    # Jog
    # ------------------------------------------------------------------

    def jog_cw(self) -> None:
        """Start jogging clockwise at the configured speed. Runs until jog_stop()."""
        self._start_jog(direction=1)

    def jog_ccw(self) -> None:
        """Start jogging counter-clockwise at the configured speed. Runs until jog_stop()."""
        self._start_jog(direction=-1)

    def jog_stop(self) -> None:
        """Stop an active jog (or any in-progress move) with a deceleration ramp."""
        with self._axis_lock:
            self._jogging = False
            self._goal = None
        self._motor.stop()

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    @property
    def position(self) -> float:
        """Current axis position in degrees, normalised to [0, 360)."""
        return self._motor.position

    @property
    def speed(self) -> float:
        """Instantaneous shaft speed in degrees per second."""
        return self._motor.speed

    @property
    def is_moving(self) -> bool:
        """True while the axis is in motion (move or jog)."""
        return self._motor.is_running

    @property
    def motor(self) -> ServoMotor:
        """Direct access to the underlying ServoMotor (read-only by convention)."""
        return self._motor

    def __repr__(self) -> str:
        goal_str = f"{self._goal % 360.0:.2f}°" if self._goal is not None else "none"
        return (
            f"RotaryAxis("
            f"pos={self.position:.2f}°, "
            f"speed={self.speed:.1f}°/s, "
            f"motor={self._motor.state}, "
            f"goal={goal_str})"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _start_move(self, delta_deg: float) -> None:
        """Common entry point for absolute and relative moves."""
        # Cancel any ongoing move / jog
        with self._axis_lock:
            self._jogging = False
            self._goal = self._motor.raw_position + delta_deg

        self._motor.stop()
        # Wait for full stop before committing to the new direction
        while self._motor.is_running:
            time.sleep(0.005)

        if abs(delta_deg) < self._POSITION_TOLERANCE:
            return   # already there

        direction = 1 if delta_deg > 0 else -1
        self._motor.set_direction(direction)

        with self._axis_lock:
            thread = threading.Thread(
                target=self._move_loop,
                args=(self._goal,),
                daemon=True,
            )
            self._move_thread = thread
        thread.start()

    def _start_jog(self, direction: int) -> None:
        """Common entry point for jog CW / CCW."""
        with self._axis_lock:
            self._jogging = True
            self._goal = None

        self._motor.stop()
        while self._motor.is_running:
            time.sleep(0.005)

        self._motor.set_direction(direction)
        self._motor.start()

    def _move_loop(self, goal_raw: float) -> None:
        """
        Background thread that watches position and triggers deceleration at
        the right moment so the motor coasts to a stop exactly at the goal.

        Uses the kinematic relation:  braking_distance = v^2 / (2 * a)

        Edge cases handled
        ------------------
        - Negative delta (CCW): remaining is clamped >= 0 so overshoot is
          treated as arrival rather than causing an infinite loop.
        - Short moves (delta < min braking distance): stop() is commanded on
          the first tick; we exit once the motor fully halts rather than
          waiting for a position threshold that may never be crossed.
        """
        self._motor.start()
        stop_commanded = False

        while True:
            with self._motor._lock:
                v         = self._motor._speed
                a         = self._motor._acceleration
                raw       = self._motor._position
                direction = self._motor._direction

            # Positive while en-route; clamped to 0 on overshoot so arrival
            # is always detected even if the motor coasts past the target.
            remaining = max(direction * (goal_raw - raw), 0.0)

            # Check for cancellation
            with self._axis_lock:
                if self._goal != goal_raw:
                    return

            # Deceleration lookahead: distance needed to brake from v to 0
            braking_dist = (v * v) / (2.0 * a) if a > 0 else 0.0

            if remaining <= braking_dist + self._POSITION_TOLERANCE:
                self._motor.stop()
                stop_commanded = True

            # Arrival: within tolerance, OR stop was commanded and the motor
            # has fully halted (handles very short moves cleanly).
            arrived = remaining <= self._POSITION_TOLERANCE or (
                stop_commanded and not self._motor.is_running
            )
            if arrived:
                with self._axis_lock:
                    if self._goal == goal_raw:
                        self._goal = None
                return

            time.sleep(0.002)   # 500 Hz polling