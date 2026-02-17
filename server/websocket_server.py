import asyncio
import json

import websockets

from scene.scene import Scene


class WebSocketServer:
    def __init__(self, scene: Scene, host: str = "localhost", port: int = 8765,
                 update_interval: float = 0.05):
        """
        :param scene: Scene object to stream snapshots from
        :param host: WebSocket server host
        :param port: WebSocket server port
        :param update_interval: How often to send snapshots (in seconds)
        """
        self.scene = scene
        self.host = host
        self.port = port
        self.update_interval = update_interval
        self.clients: set = set()

    async def handler(self, websocket):
        print(f"[ws] Client connected: {websocket.remote_address}")
        self.clients.add(websocket)

        # Send scene definition on initial connection
        try:
            scene_definition = self.scene.static_scene_definition()
            await websocket.send(json.dumps(scene_definition))
            print(f"[ws] Sent scene definition to {websocket.remote_address}")
        except websockets.ConnectionClosed:
            self.clients.discard(websocket)
            print(f"[ws] Client disconnected during scene definition send: {websocket.remote_address}")
            return

        try:
            await websocket.wait_closed()
        finally:
            self.clients.discard(websocket)
            print(f"[ws] Client disconnected: {websocket.remote_address}")

    async def broadcast_snapshots(self):
        """Continuously sends the scene snapshot to all connected clients."""
        while True:
            if self.clients:
                snapshot_data = self.scene.snapshot()
                message = json.dumps(snapshot_data)
                # Send to each client, removing any that have disconnected
                disconnected = set()
                for client in self.clients:
                    try:
                        await client.send(message)
                    except websockets.ConnectionClosed:
                        disconnected.add(client)
                self.clients -= disconnected
            await asyncio.sleep(self.update_interval)

    async def start(self):
        server = await websockets.serve(self.handler, self.host, self.port)
        print(f"[ws] WebSocket server started on ws://{self.host}:{self.port}")
        await self.broadcast_snapshots()
        await server.wait_closed()

    def run(self):
        asyncio.run(self.start())