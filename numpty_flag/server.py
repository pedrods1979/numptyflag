import asyncio
import json
import logging

import websockets

from .threat_engine import ThreatEngine

logger = logging.getLogger(__name__)


class OverlayServer:
    """Broadcasts threat-engine snapshots to connected overlay clients."""

    def __init__(self, engine: ThreatEngine, host: str = "localhost", port: int = 8765, hz: float = 4.0):
        self.engine = engine
        self.host = host
        self.port = port
        self.interval = 1.0 / hz
        self._clients: set = set()

    async def _handler(self, websocket):
        self._clients.add(websocket)
        try:
            async for _ in websocket:
                pass  # overlay clients are read-only
        finally:
            self._clients.discard(websocket)

    async def _safe_send(self, ws, payload: str) -> None:
        try:
            await ws.send(payload)
        except websockets.ConnectionClosed:
            self._clients.discard(ws)

    async def _broadcast_loop(self) -> None:
        while True:
            await asyncio.sleep(self.interval)
            if not self._clients:
                continue
            payload = json.dumps(self.engine.build_payload())
            await asyncio.gather(
                *(self._safe_send(ws, payload) for ws in list(self._clients)),
                return_exceptions=True,
            )

    async def run(self) -> None:
        async with websockets.serve(self._handler, self.host, self.port):
            logger.info("Overlay server listening on ws://%s:%s", self.host, self.port)
            await self._broadcast_loop()
