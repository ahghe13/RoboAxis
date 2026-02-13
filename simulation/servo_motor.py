"""
servo_motor.py
--------------
Rotary axis simulator with realistic acceleration and deceleration profiles.

Usage:
    motor = ServoMotor(max_speed=360.0, acceleration=90.0)
    motor.start()
    time.sleep(2)
    print(motor.position)   # degrees
    motor.stop()
"""

import threading
import time
import math


class ServoMotor:
    """
    Simulates a rotary servo motor with trapezoidal velocity profiling.

    The motor accelerates from 0 to `max_speed` (deg/s) at a configurable
    `acceleration` rate (deg/s²), runs at full speed, then decelerates
    symmetrically back to 0 when stopped.

    All simulation runs on a background daemon thread; the public API is
    fully thread-safe.

    Parameters
    ----------
    max_speed    : float  Target cruising speed in degrees per second (default 360).
    acceleration : float  Rate of speed change in degrees per second² (default 90).
    direction    : int    +1 for clockwise, -1 for counter-clockwise (default +1).
    tick_rate    : float  Simulation update frequency in Hz (default 200).
    """

    def __init__(
        self,
        max_speed: float = 360.0,
        acceleration: float = 90.0,
        direction: int = 1,
        tick_rate: float = 200.0,
    ):
        if max_speed <= 0:
            raise ValueError("max_speed must be positive.")
        if acceleration <= 0:
            raise ValueError("acceleration must be positive.")
        if direction not in (1, -1):
            raise ValueError("direction must be +1 or -1.")

        self._max_speed = float(max_speed)
        self._acceleration = float(acceleration)
        self._direction = direction
        self._tick_interval = 1.0 / tick_rate

        # Internal state (protected by _lock)
        self._lock = threading.Lock()
        self._position: float = 0.0   # degrees, unbounded (wraps for display)
        self._speed: float = 0.0      # current speed, deg/s  (always >= 0)
        self._running: bool = False   # True while motor should be spinning/accel
        self._decelerating: bool = False  # True during stop ramp-down

        # Background simulation thread
        self._thread = threading.Thread(target=self._simulate, daemon=True)
        self._thread.start()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """
        Command the motor to begin rotating.

        The motor will ramp up from its current speed to `max_speed` using
        the configured acceleration profile.  Calling start() while already
        running has no effect.
        """
        with self._lock:
            if self._running and not self._decelerating:
                return  # already at cruise — nothing to do
            self._running = True
            self._decelerating = False

    def stop(self) -> None:
        """
        Command the motor to decelerate to a stop.

        The motor will ramp down from its current speed to 0.  Calling
        stop() on an already-stopped motor has no effect.
        """
        with self._lock:
            if not self._running and self._speed == 0.0:
                return
            self._running = False
            self._decelerating = True

    @property
    def position(self) -> float:
        """
        Current angular position in degrees, normalised to [0, 360).
        """
        with self._lock:
            return self._position % 360.0

    @property
    def raw_position(self) -> float:
        """
        Cumulative angular position in degrees (unbounded — counts full
        rotations, so e.g. 720° means exactly two full turns from start).
        """
        with self._lock:
            return self._position

    @property
    def speed(self) -> float:
        """Current rotational speed in degrees per second."""
        with self._lock:
            return self._speed

    @property
    def is_running(self) -> bool:
        """True if the motor is moving (including during ramp-up/down)."""
        with self._lock:
            return self._speed > 0.0

    @property
    def state(self) -> str:
        """Human-readable motor state: 'idle', 'accelerating', 'cruising', or 'decelerating'."""
        with self._lock:
            if self._speed == 0.0 and not self._running:
                return "idle"
            if self._decelerating:
                return "decelerating"
            if self._running and self._speed < self._max_speed:
                return "accelerating"
            return "cruising"

    def reset_position(self) -> None:
        """Zero the position counter (motor may still be moving)."""
        with self._lock:
            self._position = 0.0

    def set_direction(self, direction: int) -> None:
        """
        Change rotation direction (+1 or -1).

        For a clean direction reversal, stop the motor first.
        """
        if direction not in (1, -1):
            raise ValueError("direction must be +1 or -1.")
        with self._lock:
            self._direction = direction

    # ------------------------------------------------------------------
    # Simulation loop (runs in background thread)
    # ------------------------------------------------------------------

    def _simulate(self) -> None:
        """Background thread: advances position using a trapezoidal velocity profile."""
        last_time = time.perf_counter()

        while True:
            time.sleep(self._tick_interval)
            now = time.perf_counter()
            dt = now - last_time
            last_time = now

            with self._lock:
                if self._running:
                    # Accelerate toward max_speed
                    if self._speed < self._max_speed:
                        self._speed = min(
                            self._speed + self._acceleration * dt,
                            self._max_speed,
                        )
                elif self._decelerating:
                    # Decelerate toward zero
                    if self._speed > 0.0:
                        self._speed = max(
                            self._speed - self._acceleration * dt,
                            0.0,
                        )
                    if self._speed == 0.0:
                        self._decelerating = False

                # Integrate position
                self._position += self._direction * self._speed * dt

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"ServoMotor("
            f"state={self.state!r}, "
            f"position={self.position:.2f}°, "
            f"speed={self.speed:.1f} deg/s)"
        )


# ---------------------------------------------------------------------------
# Main — runs when the module is executed directly
# ---------------------------------------------------------------------------

def _print_loop(motor: ServoMotor, stop_event: threading.Event) -> None:
    """Prints motor state every 100 ms until stop_event is set."""
    t0 = time.perf_counter()
    while not stop_event.is_set():
        elapsed = time.perf_counter() - t0
        bar_len = int(motor.speed / motor._max_speed * 30)
        bar = "█" * bar_len + "░" * (30 - bar_len)
        print(
            f"  t={elapsed:6.2f}s | {motor.state:<13} | "
            f"{motor.speed:6.1f}°/s | {motor.position:7.2f}° [{bar}]"
        )
        time.sleep(0.1)


def main() -> None:
    # 1. Create motor
    motor = ServoMotor(max_speed=360.0, acceleration=90.0)
    print("Motor created.\n")

    # 2. Kick off the parallel print loop in a background thread
    stop_printing = threading.Event()
    printer = threading.Thread(target=_print_loop, args=(motor, stop_printing), daemon=True)
    printer.start()

    # 3. Start the motor and wait until it reaches cruising speed
    motor.start()
    print(">>> Motor started — waiting for cruise speed …\n")
    while motor.state != "cruising":
        time.sleep(0.01)

    # 4. Cruise for 5 seconds
    print("\n>>> Cruising — waiting 5 seconds …\n")
    time.sleep(5)

    # 5. Stop the motor
    motor.stop()
    print("\n>>> Motor stopping — waiting for full stop …\n")

    # 6. Stay alive until the motor has fully stopped
    while motor.is_running:
        time.sleep(0.01)

    # 7. Shut down the print loop and wait for it to finish its current tick
    stop_printing.set()
    printer.join()

    print(f"\nMotor stopped. Final position: {motor.position:.2f}°  "
          f"({motor.raw_position / 360:.2f} total turns)")


if __name__ == "__main__":
    main()