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
import json
import pathlib
import signal
import sys
import threading
import time

from server.websocket_server import WebSocketServer
from scene.scene import Scene
from server import FrontendServer
from kinematics import SerialRobot


def main() -> None:
    parser = argparse.ArgumentParser(description="Rotary axis simulator")
    parser.add_argument("--host",         default="localhost", help="Bind address (default: localhost)")
    parser.add_argument("--port",         default=8080,        type=int,   help="HTTP port (default: 8080)")
    parser.add_argument("--ws-port",      default=8765,        type=int,   help="WebSocket port (default: 8765)")
    parser.add_argument("--max-speed",    default=180.0,       type=float, help="Max speed in °/s (default: 180)")
    parser.add_argument("--acceleration", default=60.0,        type=float, help="Acceleration in °/s² (default: 60)")
    args = parser.parse_args()

    scene = Scene()

    robot_file = pathlib.Path(__file__).parent / "devices" / "robots" / "robot_3dof.json"
    robot_desc = json.loads(robot_file.read_text())
    robot = SerialRobot(robot_desc)
    scene.add_child(robot)

    server = FrontendServer(host=args.host, port=args.port, scene=scene, ws_port=args.ws_port)

    ws_server = WebSocketServer(scene, host=args.host, port=args.ws_port, update_interval=0.05)
    ws_thread = threading.Thread(target=ws_server.run, daemon=True)
    ws_thread.start()

    server.start()
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