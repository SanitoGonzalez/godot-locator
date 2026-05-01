"""End-to-end smoke for the MCP layer.

Drives the FastMCP server in-process via its in-memory client, against a real
Godot subprocess (`locator_client` fixture). Verifies the full stack — tool
dispatch → LocatorClient → plugin — answers a basic `snapshot()` call without
errors. Per-tool behavior lives in dedicated tests.
"""

from __future__ import annotations

import pytest
from fastmcp import Client

from godot_locator_core import LocatorClient
from godot_locator_mcp import mcp
from godot_locator_mcp.server import _set_client


@pytest.mark.godot_project("simple-ui")
async def test_snapshot(locator_client: LocatorClient) -> None:
    _set_client(locator_client)
    try:
        async with Client(mcp) as client:
            result = await client.call_tool("snapshot")
        assert not result.is_error
    finally:
        _set_client(None)
