"""Async WebSocket client for the godot-locator runtime service.

Mirrors the wire the Godot side speaks: JSON requests of shape
``{"id": int, "method": str, "params": dict}`` and responses of shape
``{"id": int, "result": ...}`` or ``{"id": int, "error": ...}``.

The client connects lazily on the first ``call`` and keeps the socket open
across calls. If the socket drops between calls it transparently reconnects.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlparse

import websockets
from websockets.asyncio.client import ClientConnection

from .errors import LocatorError


class LocatorClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 8282) -> None:
        self.host = host
        self.port = port
        self.url = f"ws://{host}:{port}"
        self._ws: ClientConnection | None = None
        self._next_id = 0
        # Serialize request/response across concurrent tool calls. The wire
        # is request/response with monotonically-increasing ids; without a
        # lock interleaved sends could swap responses.
        self._lock = asyncio.Lock()

    @classmethod
    def from_endpoint(cls, endpoint: str) -> LocatorClient:
        """Build a client from a `ws://host:port` URL — the form session
        files store. Falls back to defaults for missing components."""
        parsed = urlparse(endpoint)
        if parsed.scheme not in ("ws", ""):
            raise ValueError(f"unsupported scheme in endpoint {endpoint!r} (need ws://)")
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 8282
        return cls(host=host, port=port)

    async def call(self, method: str, **params: Any) -> Any:
        async with self._lock:
            ws = await self._connect()
            self._next_id += 1
            request = {"id": self._next_id, "method": method, "params": params}
            try:
                await ws.send(json.dumps(request))
                response = json.loads(await ws.recv())
            except websockets.ConnectionClosed:
                # Drop the dead socket so the next call reconnects.
                self._ws = None
                raise LocatorError(
                    f"connection to {self.url} closed mid-call — has the Godot game exited?"
                ) from None
        if "error" in response:
            raise LocatorError(response["error"])
        return response.get("result")

    async def _connect(self) -> ClientConnection:
        if self._ws is not None:
            return self._ws
        try:
            self._ws = await websockets.connect(self.url)
        except (OSError, ConnectionRefusedError) as e:
            raise LocatorError(
                f"can't reach godot-locator at {self.url} — is your Godot game running with the godot-locator plugin?"
            ) from e
        return self._ws

    async def close(self) -> None:
        if self._ws is not None:
            try:
                await self._ws.close()
            finally:
                self._ws = None
