"""
main.py
-------
Demo script for the rotary axis simulator.

Run with:
    python main.py
"""

import threading
import time

from simulation import ServoMotor, RotaryAxis


# ---------------------------------------------------------------------------
# Helpers
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


def section(msg: str) -> None:
    print(f"\n{'─' * 58}")
    print(f"  {msg}")
    print(f"{'─' * 58}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 58)
    print("  RotaryAxis demo")
    print("=" * 58)

    axis = RotaryAxis(max_speed=180.0, acceleration=60.0)

    # Parallel print loop — reports axis position every 100 ms
    stop_printing = threading.Event()
    printer = threading.Thread(
        target=_print_loop,
        args=(axis.motor, stop_printing),
        daemon=True,
    )
    printer.start()

    # ── 1. Jog CW for 2 seconds ──────────────────────────────────
    section("Jog CW for 2 s")
    axis.jog_cw()
    time.sleep(2)
    axis.jog_stop()
    while axis.is_moving:
        time.sleep(0.01)
    print(f"\n  >> Stopped at {axis.position:.2f}°")

    # ── 2. Set speed and acceleration at runtime ──────────────────
    section("Tuning: speed → 120 °/s, acceleration → 90 °/s²")
    axis.set_speed(120.0)
    axis.set_acceleration(90.0)

    # ── 3. Absolute move to 270° ──────────────────────────────────
    section("Absolute move → 200°")
    axis.set_absolute_position(200.0)
    axis.wait_for_move()
    print(f"\n  >> Arrived at {axis.position:.2f}°  (target 270°)")

    # ── 4. Relative move +90° (should land on ~0°/360°) ──────────
    section("Relative move -90°")
    axis.set_relative_position(-90.0)
    axis.wait_for_move()
    print(f"\n  >> Arrived at {axis.position:.2f}°  (target 0°/360°)")

    # ── 5. Absolute move to 45° ───────────────────────────────────
    section("Absolute move → 45°")
    axis.set_absolute_position(45.0)
    axis.wait_for_move()
    print(f"\n  >> Arrived at {axis.position:.2f}°  (target 45°)")

    # ── 6. Jog CCW for 1.5 seconds ───────────────────────────────
    section("Jog CCW for 1.5 s")
    axis.jog_ccw()
    time.sleep(1.5)
    axis.jog_stop()
    while axis.is_moving:
        time.sleep(0.01)
    print(f"\n  >> Stopped at {axis.position:.2f}°")

    # ── Done ──────────────────────────────────────────────────────
    stop_printing.set()
    printer.join()
    print(f"\n{'=' * 58}")
    print(f"  Demo complete.  Final position: {axis.position:.2f}°")
    print(f"{'=' * 58}")


if __name__ == "__main__":
    main()