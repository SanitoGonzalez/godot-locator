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

import websockets
from websockets.asyncio.client import ClientConnection


class LocatorError(RuntimeError):
    """Raised for both transport failures (socket refused, dropped) and
    protocol-level errors (the Godot side returned an ``error`` field).
    The MCP layer maps this to a tool error so the model sees the message."""


class LocatorClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 8282) -> None:
        self.url = f"ws://{host}:{port}"
        self._ws: ClientConnection | None = None
        self._next_id = 0
        # Serialize request/response across concurrent tool calls. The wire
        # is request/response with monotonically-increasing ids; without a
        # lock interleaved sends could swap responses.
        self._lock = asyncio.Lock()

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
