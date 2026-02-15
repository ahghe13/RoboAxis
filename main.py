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
import threading
import time

from server.websocket_server import WebSocketServer
from simulation import RotaryAxis
from axis_math import Transform
from scene import Scene
from server import FrontendServer
from devices import ThreeAxisRobot


def main() -> None:
    parser = argparse.ArgumentParser(description="Rotary axis simulator")
    parser.add_argument("--host",         default="localhost", help="Bind address (default: localhost)")
    parser.add_argument("--port",         default=8080,        type=int,   help="HTTP port (default: 8080)")
    parser.add_argument("--ws-port",      default=8765,        type=int,   help="WebSocket port (default: 8765)")
    parser.add_argument("--max-speed",    default=180.0,       type=float, help="Max speed in °/s (default: 180)")
    parser.add_argument("--acceleration", default=60.0,        type=float, help="Acceleration in °/s² (default: 60)")
    args = parser.parse_args()

    scene = Scene()

    # Add individual rotary axes
    scene.add("axis_1", RotaryAxis(max_speed=args.max_speed, acceleration=args.acceleration),
              transform=Transform(position=(1, 0, 0)))
    scene.add("axis_2", RotaryAxis(max_speed=args.max_speed, acceleration=args.acceleration),
              parent="axis_1", transform=Transform(position=(0, 0, 1)))

    # Add 3-axis robot (treat as a single component for now)
    robot = ThreeAxisRobot()
    robot.set_joint_angles(shoulder=45.0, elbow=45.0, wrist=0.0)
    scene.add("robot", robot, transform=Transform(position=(-2, 0, 0)))

    server = FrontendServer(host=args.host, port=args.port, scene=scene, ws_port=args.ws_port)

    ws_server = WebSocketServer(scene, host=args.host, port=args.ws_port, update_interval=0.05)
    ws_thread = threading.Thread(target=ws_server.run, daemon=True)
    ws_thread.start()

    server.start()
    print(f"  Scene — components: {scene.names()}")
    print(f"  Axis  — max speed: {args.max_speed} °/s  |  accel: {args.acceleration} °/s²")
    print(f"  WebSocket — ws://{args.host}:{args.ws_port}")
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