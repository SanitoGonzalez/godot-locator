"""Tiny WebSocket client used by integration tests.

Mirrors the wire the MCP bridge will speak: JSON requests of shape
``{"id": int, "method": str, "params": dict}`` and responses of shape
``{"id": int, "result": ...}`` or ``{"id": int, "error": ...}``.
"""

from __future__ import annotations

import json

import websockets


class LocatorError(RuntimeError):
    pass


class Client:
    def __init__(self, port: int, host: str = "127.0.0.1") -> None:
        self.url = f"ws://{host}:{port}"
        self._next_id = 0
        self._ws: websockets.WebSocketClientProtocol | None = None

    async def __aenter__(self) -> "Client":
        self._ws = await websockets.connect(self.url)
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None

    async def call(self, method: str, **params: object) -> object:
        assert self._ws is not None, "client not connected — use `async with Client(port)`"
        self._next_id += 1
        request = {"id": self._next_id, "method": method, "params": params}
        await self._ws.send(json.dumps(request))
        response = json.loads(await self._ws.recv())
        if "error" in response:
            raise LocatorError(response["error"])
        return response.get("result")
