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
    POST /api/scene/<id>/position    → set target position for an axis
    POST /api/scene/<id>/joints      → set joint angles for a ThreeAxisRobot
                                       body: {"shoulder": deg, "elbow": deg, "wrist": deg}
                                       all fields optional; omitted joints keep current angle
"""
from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scene import Scene


class Handler(BaseHTTPRequestHandler):
    """Single-use request handler created per-connection by HTTPServer."""

    static_dir: Path
    scene: Scene | None
    ws_port: int

    def do_GET(self) -> None:
        path = self.path.split("?")[0]  # strip query string

        if path == "/" or path == "/index.html":
            self._serve_file(self.static_dir / "index.html")
        elif path.startswith("/static/"):
            self._serve_file(self.static_dir / path[len("/static/"):])
        elif path == "/api/scene":
            self._serve_scene()
        elif path == "/api/scene/definition":
            self._serve_scene_definition()
        elif path == "/api/config":
            self._send_json(200, {"ws_port": self.ws_port})
        else:
            self._send_error(404, f"Not found: {path}")

    def do_POST(self) -> None:
        path = self.path.split("?")[0]
        parts = path.strip("/").split("/")

        if len(parts) == 4 and parts[0] == "api" and parts[1] == "scene":
            name, action = parts[2], parts[3]
            if action == "position":
                self._set_position(name)
            elif action == "joints":
                self._set_joint_angles(name)
            else:
                self._send_error(404, f"Not found: {path}")
        else:
            self._send_error(404, f"Not found: {path}")

    def _set_position(self, name: str) -> None:
        if self.scene is None:
            self._send_error(503, "No scene available")
            return

        try:
            component = self.scene.get(name)
        except KeyError:
            self._send_error(404, f"Component not found: {name}")
            return

        if not hasattr(component, "set_absolute_position"):
            self._send_error(400, f"Component '{name}' is not a positionable axis")
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            target = float(body["target"])
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            self._send_error(400, f"Invalid request body: {e}")
            return

        component.set_absolute_position(target)
        self._send_json(200, {"name": name, "target": target})

    def _set_joint_angles(self, name: str) -> None:
        if self.scene is None:
            self._send_error(503, "No scene available")
            return

        try:
            component = self.scene.get(name)
        except KeyError:
            self._send_error(404, f"Component not found: {name}")
            return

        if not hasattr(component, "set_joint_angles") or not hasattr(component, "get_joint_angles"):
            self._send_error(400, f"Component '{name}' does not support joint control")
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, ValueError) as e:
            self._send_error(400, f"Invalid request body: {e}")
            return

        current = component.get_joint_angles()
        try:
            angles = {
                "shoulder": float(body.get("shoulder", current["shoulder"])),
                "elbow":    float(body.get("elbow",    current["elbow"])),
                "wrist":    float(body.get("wrist",    current["wrist"])),
            }
        except (ValueError, TypeError) as e:
            self._send_error(400, f"Invalid angle value: {e}")
            return

        component.set_joint_angles(**angles)
        self._send_json(200, {"name": name, "joints": angles})

    def _serve_scene(self) -> None:
        if self.scene is None:
            self._send_error(503, "No scene available")
            return
        data = json.dumps(self.scene.snapshot()).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_scene_definition(self) -> None:
        if self.scene is None:
            self._send_error(503, "No scene available")
            return
        self._send_json(200, self.scene.static_scene_definition())

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
