"""
server
------
HTTP server package.

Re-exports FrontendServer so callers can write::

    from server import FrontendServer
"""

from server.server import FrontendServer

__all__ = ["FrontendServer"]
