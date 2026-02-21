"""
routes/devices.py
-----------------
DeviceRoutes mixin — handles all /api/devices/* endpoints and
the POST /api/scene/robots endpoint.

Mixed into Handler; relies on self._send_json / self._send_error
and the class attributes self.scene / self.rfile / self.headers.
"""
from __future__ import annotations

import json
from pathlib import Path

from kinematics import SerialRobot

_DEVICES_DIR = Path(__file__).parent.parent.parent / "devices"


class DeviceRoutes:

    # ── GET /api/devices/robots ───────────────────────────────────────────────

    def _list_robot_devices(self) -> None:
        robots_dir = _DEVICES_DIR / "robots"
        robots = []
        for f in sorted(robots_dir.glob("*.json")):
            try:
                desc = json.loads(f.read_text())
                robots.append({
                    "filename": f.name,
                    "name": desc.get("name", f.stem),
                    "joint_count": len(desc.get("joints", [])),
                })
            except Exception:
                pass
        self._send_json(200, robots)

    # ── POST /api/scene/robots ────────────────────────────────────────────────

    def _add_robot(self) -> None:
        if self.scene is None:
            self._send_error(503, "No scene available")
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            filename = str(body["device"])
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            self._send_error(400, f"Invalid request body: {e}")
            return

        if "/" in filename or "\\" in filename or not filename.endswith(".json"):
            self._send_error(400, "Invalid device filename")
            return

        robot_path = _DEVICES_DIR / "robots" / filename
        if not robot_path.exists():
            self._send_error(404, f"Device not found: {filename}")
            return

        try:
            desc = json.loads(robot_path.read_text())
            robot = SerialRobot(desc)
        except Exception as e:
            self._send_error(500, f"Failed to load robot: {e}")
            return

        self.scene.add_child(robot)
        self._send_json(201, {"added": robot.static_definition()})