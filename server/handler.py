"""
handler.py
----------
HTTP request handler for the frontend server.

Routes:
    GET  /                           → index.html
    GET  /static/<path>              → static file from the frontend directory
    GET  /api/scene                  → JSON snapshot of the scene (dynamic state)
    GET  /api/scene/definition       → static scene definition (structure only)
    GET  /api/config                 → server configuration (ws_port, etc.)
    GET  /api/devices/robots         → list robot descriptors in devices/robots/
    POST /api/scene/<id>/position    → set target position for an axis
    POST /api/scene/<id>/joints      → set joint angles for a SerialRobot
    POST /api/scene/<id>/jog         → jog a joint on a SerialRobot
    POST /api/scene/<id>/transform   → update the local transform of any component
    POST /api/scene/robots           → instantiate a robot from a device file and add to scene

Route implementations live in server/routes/.
"""
from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import TYPE_CHECKING

from server.routes.scene   import SceneRoutes
from server.routes.devices import DeviceRoutes

if TYPE_CHECKING:
    from scene.scene import Scene


class Handler(SceneRoutes, DeviceRoutes, BaseHTTPRequestHandler):
    """Single-use request handler created per-connection by HTTPServer."""

    static_dir: Path
    scene: Scene | None
    ws_port: int

    # ── Routing ───────────────────────────────────────────────────────────────

    def do_GET(self) -> None:
        path = self.path.split("?")[0]

        if path in ("/", "/index.html"):
            self._serve_file(self.static_dir / "index.html")
        elif path.startswith("/static/"):
            self._serve_file(self.static_dir / path[len("/static/"):])
        elif path == "/api/scene":
            self._serve_scene()
        elif path == "/api/scene/definition":
            self._serve_scene_definition()
        elif path == "/api/config":
            self._send_json(200, {"ws_port": self.ws_port})
        elif path == "/api/devices/robots":
            self._list_robot_devices()
        else:
            self._send_error(404, f"Not found: {path}")

    def do_POST(self) -> None:
        path  = self.path.split("?")[0]
        parts = path.strip("/").split("/")

        if parts == ["api", "scene", "robots"]:
            self._add_robot()
        elif len(parts) == 4 and parts[0] == "api" and parts[1] == "scene":
            name, action = parts[2], parts[3]
            if action == "position":
                self._set_position(name)
            elif action == "joints":
                self._set_joint_angles(name)
            elif action == "jog":
                self._jog_joint(name)
            elif action == "transform":
                self._set_transform(name)
            else:
                self._send_error(404, f"Not found: {path}")
        else:
            self._send_error(404, f"Not found: {path}")

    # ── Static file serving ───────────────────────────────────────────────────

    def _serve_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self._send_error(404, f"File not found: {path.name}")
            return

        mime, _ = mimetypes.guess_type(str(path))
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ── Response helpers ──────────────────────────────────────────────────────

    def _send_json(self, code: int, obj: object) -> None:
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_error(self, code: int, message: str) -> None:
        body = message.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        """Silence the default per-request stdout noise."""
        pass