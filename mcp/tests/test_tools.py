"""Exercises each MCP tool end-to-end against a real headless Godot.

We assert against snapshot text rather than reading internal state, mirroring
the strategy from the top-level ``tests/`` suite.
"""

from __future__ import annotations

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError


async def _snapshot_text(client: Client, **params) -> str:
    result = await client.call_tool("snapshot", params)
    return result.data


async def test_snapshot_returns_yaml_string(mcp_client: Client) -> None:
    text = await _snapshot_text(mcp_client)
    assert isinstance(text, str)
    assert "VBoxContainer" in text


async def test_snapshot_tags_refs_by_default(mcp_client: Client) -> None:
    """The MCP layer flips Godot's default — agents almost always want refs."""
    text = await _snapshot_text(mcp_client)
    assert "ref=e" in text


async def test_snapshot_tag_ref_false_omits_refs(mcp_client: Client) -> None:
    text = await _snapshot_text(mcp_client, tag_ref=False)
    assert "ref=" not in text


async def test_click_updates_status_label(mcp_client: Client) -> None:
    await mcp_client.call_tool("click", {"locator": {"name": "Submit"}})
    text = await _snapshot_text(mcp_client)
    assert "submitted: " in text


async def test_double_click_updates_status_label(mcp_client: Client) -> None:
    await mcp_client.call_tool("double_click", {"locator": {"name": "ClickPad"}})
    text = await _snapshot_text(mcp_client)
    assert "double-clicked" in text


async def test_right_click_updates_status_label(mcp_client: Client) -> None:
    await mcp_client.call_tool("right_click", {"locator": {"name": "ClickPad"}})
    text = await _snapshot_text(mcp_client)
    assert "right-clicked" in text


async def test_fill_writes_text_and_emits_changed(mcp_client: Client) -> None:
    await mcp_client.call_tool("fill", {"locator": {"name": "NameInput"}, "text": "Sanito"})
    text = await _snapshot_text(mcp_client)
    # CharCounter listens on text_changed; "6/20" proves the signal fired.
    assert 'text="Sanito"' in text
    assert "6/20" in text


async def test_unknown_locator_raises_tool_error(mcp_client: Client) -> None:
    with pytest.raises(ToolError) as exc:
        await mcp_client.call_tool("click", {"locator": {"name": "NoSuchNode"}})
    assert "no matches" in str(exc.value).lower()
