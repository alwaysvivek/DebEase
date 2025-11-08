"""WebSocket manager: track connections and broadcast events."""

import asyncio
import json
from typing import Set
from fastapi import WebSocket

class WSManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self.active.add(ws)

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            self.active.discard(ws)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients. Best-effort non-blocking sends."""
        data = json.dumps(message)
        to_remove = []
        async with self._lock:
            for ws in list(self.active):
                try:
                    # Try to send, but don't let a single slow client block everybody.
                    await asyncio.wait_for(ws.send_text(data), timeout=2.0)
                except Exception:
                    to_remove.append(ws)
            for ws in to_remove:
                self.active.discard(ws)
