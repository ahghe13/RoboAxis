"""
server.py
---------
Simple HTTP server that serves static files from the frontend directory.

Usage:
    from server import FrontendServer

    server = FrontendServer(host="localhost", port=8080)
    server.start()   # non-blocking — runs in background thread
    ...
    server.stop()

Endpoints
---------
GET  /              Serves index.html from the frontend directory.
GET  /static/<path> Serves any file from the frontend directory.
GET  /api/scene     Returns JSON snapshot of the scene.
"""
from __future__ import annotations

import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scene import Scene

_FRONTEND_DIR = Path(__file__).parent / "frontend"


class _Handler(BaseHTTPRequestHandler):
    """Single-use request handler created per-connection by HTTPServer."""

    static_dir: Path
    scene: Scene | None

    def do_GET(self) -> None:
        path = self.path.split("?")[0]  # strip query string

        if path == "/" or path == "/index.html":
            self._serve_file(self.static_dir / "index.html")
        elif path.startswith("/static/"):
            self._serve_file(self.static_dir / path[len("/static/"):])
        elif path == "/api/scene":
            self._serve_scene()
        else:
            self._send_error(404, f"Not found: {path}")

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


class FrontendServer:
    """
    Hosts static files over HTTP.

    Parameters
    ----------
    host       : str          Bind address (default "localhost").
    port       : int          TCP port (default 8080).
    static_dir : Path | None  Directory to serve files from.
                              Defaults to the same directory as this file.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        static_dir: Path | None = None,
        scene: Scene | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._static_dir = static_dir or _FRONTEND_DIR
        self._scene = scene
        self._httpd: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the HTTP server in a background daemon thread."""
        if self._thread and self._thread.is_alive():
            return

        static_dir = self._static_dir
        scene = self._scene

        class BoundHandler(_Handler):
            pass

        BoundHandler.static_dir = static_dir
        BoundHandler.scene = scene

        self._httpd = HTTPServer((self._host, self._port), BoundHandler)
        self._thread = threading.Thread(
            target=self._httpd.serve_forever,
            daemon=True,
            name="FrontendServer",
        )
        self._thread.start()
        print(f"[FrontendServer] Listening on http://{self._host}:{self._port}")

    def stop(self) -> None:
        """Shut down the HTTP server gracefully."""
        if self._httpd:
            self._httpd.shutdown()
            self._httpd = None
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        print("[FrontendServer] Stopped.")

    def __enter__(self) -> "FrontendServer":
        self.start()
        return self

    def __exit__(self, *_) -> None:
        self.stop()

    def __repr__(self) -> str:
        running = self._thread is not None and self._thread.is_alive()
        return (
            f"FrontendServer("
            f"http://{self._host}:{self._port}, "
            f"{'running' if running else 'stopped'})"
        )