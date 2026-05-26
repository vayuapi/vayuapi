"""
WebSocket support for VayuAPI
"""

from typing import Any, Dict
from starlette.websockets import WebSocket as StarletteWebSocket, WebSocketDisconnect


class WebSocket:
    """
    Enhanced WebSocket class with additional utilities.

    Wraps Starlette WebSocket with convenient methods.
    """

    def __init__(self, websocket: StarletteWebSocket):
        self._websocket = websocket
        self.client_id = None
        self.state = {}

    async def accept(self, subprotocol: str = None):
        """Accept the WebSocket connection."""
        await self._websocket.accept(subprotocol=subprotocol)

    async def close(self, code: int = 1000, reason: str = None):
        """Close the WebSocket connection."""
        await self._websocket.close(code=code, reason=reason)

    async def send_text(self, data: str):
        """Send text message."""
        await self._websocket.send_text(data)

    async def send_bytes(self, data: bytes):
        """Send binary message."""
        await self._websocket.send_bytes(data)

    async def send_json(self, data: Dict[str, Any]):
        """Send JSON message."""
        await self._websocket.send_json(data)

    async def receive_text(self) -> str:
        """Receive text message."""
        return await self._websocket.receive_text()

    async def receive_bytes(self) -> bytes:
        """Receive binary message."""
        return await self._websocket.receive_bytes()

    async def receive_json(self) -> Dict[str, Any]:
        """Receive JSON message."""
        return await self._websocket.receive_json()

    async def iter_text(self):
        """Iterate over text messages."""
        try:
            while True:
                yield await self.receive_text()
        except WebSocketDisconnect:
            pass

    async def iter_json(self):
        """Iterate over JSON messages."""
        try:
            while True:
                yield await self.receive_json()
        except WebSocketDisconnect:
            pass

    @property
    def client(self):
        """Get client information."""
        return self._websocket.client

    @property
    def headers(self):
        """Get request headers."""
        return self._websocket.headers


class WebSocketManager:
    """
    Manage multiple WebSocket connections.

    Useful for broadcasting messages to multiple clients.

    Example:
        ```python
        manager = WebSocketManager()

        @app.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str):
            await manager.connect(websocket, client_id)
            try:
                while True:
                    data = await websocket.receive_text()
                    await manager.broadcast(f"Client {client_id}: {data}")
            except WebSocketDisconnect:
                manager.disconnect(client_id)
        ```
    """

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """Register new WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        websocket.client_id = client_id

    def disconnect(self, client_id: str):
        """Remove WebSocket connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_personal_message(self, message: str, client_id: str):
        """Send message to specific client."""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_text(message)

    async def broadcast(self, message: str, exclude: str = None):
        """Broadcast message to all connected clients."""
        for client_id, websocket in self.active_connections.items():
            if client_id != exclude:
                await websocket.send_text(message)

    async def broadcast_json(self, data: Dict[str, Any], exclude: str = None):
        """Broadcast JSON to all connected clients."""
        for client_id, websocket in self.active_connections.items():
            if client_id != exclude:
                await websocket.send_json(data)

    def get_connection(self, client_id: str) -> WebSocket:
        """Get WebSocket connection by client ID."""
        return self.active_connections.get(client_id)

    @property
    def connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)
