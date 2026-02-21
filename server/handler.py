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
    POST /api/scene/<id>/joints      → set joint angles for a SerialRobot
                                       body: {"joints": [deg0, deg1, ...]}
                                       list is 0-indexed; null entries skip that joint;
                                       a shorter list leaves trailing joints unchanged
    POST /api/scene/<id>/jog         → jog a joint on a SerialRobot
                                       body: {"joint": index, "direction": "cw"|"ccw"|"stop"}
    POST /api/scene/<id>/transform   → update the local transform of any component
                                       body: {"position": [x,y,z],   (all keys optional)
                                              "rotation": [rx,ry,rz],
                                              "scale":    [sx,sy,sz]}
    GET  /api/devices/robots         → list robot descriptors in devices/robots/
    POST /api/scene/robots           → instantiate a robot from a device file and add to scene
                                       body: {"device": "robot_6dof.json"}
"""
from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import TYPE_CHECKING

from axis_math.axis_math import Transform
from kinematics import SerialRobot

if TYPE_CHECKING:
    from scene.scene import Scene


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
        elif path == "/api/devices/robots":
            self._list_robot_devices()
        else:
            self._send_error(404, f"Not found: {path}")

    def do_POST(self) -> None:
        path = self.path.split("?")[0]
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
            component = self.scene.get_component(name)
        except KeyError:
            self._send_error(404, f"Component not found: {name}")
            return

        if not hasattr(component, "set_joint_angle") or not hasattr(component, "joints"):
            self._send_error(400, f"Component '{name}' does not support joint control")
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            incoming = body["joints"]
            if not isinstance(incoming, list):
                raise ValueError("'joints' must be a list")
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self._send_error(400, f"Invalid request body: {e}")
            return

        applied: dict[int, float] = {}
        for i, value in enumerate(incoming):
            if value is None:
                continue
            if i >= len(component.joints):
                self._send_error(400, f"Joint index {i} out of range (robot has {len(component.joints)} joints)")
                return
            try:
                angle = float(value)
            except (ValueError, TypeError) as e:
                self._send_error(400, f"Invalid angle at index {i}: {e}")
                return
            component.set_joint_angle(i, angle)
            applied[i] = angle

        self._send_json(200, {"name": name, "joints": applied})

    def _set_transform(self, name: str) -> None:
        if self.scene is None:
            self._send_error(503, "No scene available")
            return

        try:
            component = self.scene.get_component(name)
        except KeyError:
            self._send_error(404, f"Component not found: {name}")
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, ValueError) as e:
            self._send_error(400, f"Invalid JSON: {e}")
            return

        try:
            current = component.transform
            position = tuple(float(v) for v in body["position"]) if "position" in body else current.position
            rotation = tuple(float(v) for v in body["rotation"]) if "rotation" in body else current.rotation
            scale    = tuple(float(v) for v in body["scale"])    if "scale"    in body else current.scale
        except (KeyError, ValueError, TypeError) as e:
            self._send_error(400, f"Invalid transform values: {e}")
            return

        component.transform = Transform(position=position, rotation=rotation, scale=scale)
        self._send_json(200, {"name": name, "transform": component.transform.to_dict()})

    def _jog_joint(self, name: str) -> None:
        if self.scene is None:
            self._send_error(503, "No scene available")
            return

        try:
            component = self.scene.get_component(name)
        except KeyError:
            self._send_error(404, f"Component not found: {name}")
            return

        if not hasattr(component, "joints"):
            self._send_error(400, f"Component '{name}' does not support jog control")
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            joint_idx = int(body["joint"])
            direction = str(body["direction"])
            if direction not in ("cw", "ccw", "stop"):
                raise ValueError(f"Invalid direction '{direction}'")
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            self._send_error(400, f"Invalid request body: {e}")
            return

        if joint_idx < 0 or joint_idx >= len(component.joints):
            self._send_error(400, f"Joint index {joint_idx} out of range")
            return

        if direction == "cw":
            component.jog_cw(joint_idx)
        elif direction == "ccw":
            component.jog_ccw(joint_idx)
        else:
            component.jog_stop(joint_idx)

        self._send_json(200, {"name": name, "joint": joint_idx, "direction": direction})

    def _list_robot_devices(self) -> None:
        devices_dir = Path(__file__).parent.parent / "devices" / "robots"
        robots = []
        for f in sorted(devices_dir.glob("*.json")):
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

        # Guard against path traversal
        if "/" in filename or "\\" in filename or not filename.endswith(".json"):
            self._send_error(400, "Invalid device filename")
            return

        devices_dir = Path(__file__).parent.parent / "devices" / "robots"
        robot_path = devices_dir / filename
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

    def _serve_scene(self) -> None:
        if self.scene is None:
            self._send_error(503, "No scene available")
            return
        data = json.dumps(self.scene.get_state()).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_scene_definition(self) -> None:
        if self.scene is None:
            self._send_error(503, "No scene available")
            return
        self._send_json(200, self.scene.static_definition())

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
