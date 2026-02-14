"""
server.py
---------
FrontendServer — manages the HTTP server lifecycle in a background thread.

Usage:
    from server import FrontendServer

    server = FrontendServer(host="localhost", port=8080)
    server.start()   # non-blocking — runs in background thread
    ...
    server.stop()
"""
from __future__ import annotations

import threading
from http.server import HTTPServer
from pathlib import Path
from typing import TYPE_CHECKING

from server.handler import Handler

if TYPE_CHECKING:
    from scene import Scene

_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


class FrontendServer:
    """
    Hosts static files over HTTP.

    Parameters
    ----------
    host       : str          Bind address (default "localhost").
    port       : int          TCP port (default 8080).
    static_dir : Path | None  Directory to serve files from.
                              Defaults to the ``frontend/`` directory at project root.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        static_dir: Path | None = None,
        scene: Scene | None = None,
        ws_port: int = 8765,
    ) -> None:
        self._host = host
        self._port = port
        self._static_dir = static_dir or _FRONTEND_DIR
        self._scene = scene
        self._ws_port = ws_port
        self._httpd: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the HTTP server in a background daemon thread."""
        if self._thread and self._thread.is_alive():
            return

        static_dir = self._static_dir
        scene = self._scene

        class BoundHandler(Handler):
            pass

        BoundHandler.static_dir = static_dir
        BoundHandler.scene = scene
        BoundHandler.ws_port = self._ws_port

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
