"""
routes/scene.py
---------------
SceneRoutes mixin — handles all /api/scene/* endpoints.

Mixed into Handler; relies on self._send_json / self._send_error
and the class attributes self.scene / self.rfile / self.headers.
"""
from __future__ import annotations

import json

from axis_math.axis_math import Transform


class SceneRoutes:

    # ── GET /api/scene ────────────────────────────────────────────────────────

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

    # ── POST /api/scene/<id>/position ─────────────────────────────────────────

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

    # ── POST /api/scene/<id>/joints ───────────────────────────────────────────

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

    # ── POST /api/scene/<id>/transform ────────────────────────────────────────

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

        try:
            component.set_transform(Transform(position=position, rotation=rotation, scale=scale))
        except PermissionError as e:
            self._send_error(403, str(e))
            return

        self._send_json(200, {"name": name, "transform": component.transform.to_dict()})

    # ── POST /api/scene/<id>/jog ──────────────────────────────────────────────

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