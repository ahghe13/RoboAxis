"""
main.py
-------
Entry point for the rotary axis simulator.

Creates a RotaryAxis and starts the frontend HTTP server, then blocks
until Ctrl-C or SIGTERM.

Run with:
    python main.py
    python main.py --host 0.0.0.0 --port 8080
    python main.py --max-speed 360 --acceleration 120
"""

import argparse
import signal
import sys
import time

from rotary_axis import RotaryAxis
from server import FrontendServer


def main() -> None:
    parser = argparse.ArgumentParser(description="Rotary axis simulator")
    parser.add_argument("--host",         default="localhost", help="Bind address (default: localhost)")
    parser.add_argument("--port",         default=8080,        type=int,   help="HTTP port (default: 8080)")
    parser.add_argument("--max-speed",    default=180.0,       type=float, help="Max speed in °/s (default: 180)")
    parser.add_argument("--acceleration", default=60.0,        type=float, help="Acceleration in °/s² (default: 60)")
    args = parser.parse_args()

    axis   = RotaryAxis(max_speed=args.max_speed, acceleration=args.acceleration)
    server = FrontendServer(host=args.host, port=args.port)

    server.start()
    print(f"  Axis  — max speed: {args.max_speed} °/s  |  accel: {args.acceleration} °/s²")
    print("  Press Ctrl-C to stop.\n")

    def _shutdown(sig, frame) -> None:
        print("\n[main] Shutting down …")
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()