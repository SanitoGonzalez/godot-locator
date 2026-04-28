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
    # `.structured_content` is the raw interaction-response dict; `.data` is the
    # parsed Pydantic model (attribute access). Tests use the dict for clarity.
    result = await mcp_client.call_tool("click", {"locator": {"name": "Submit"}})
    assert "submitted: " in result.structured_content["snapshot"]


async def test_double_click_updates_status_label(mcp_client: Client) -> None:
    result = await mcp_client.call_tool("double_click", {"locator": {"name": "ClickPad"}})
    assert "double-clicked" in result.structured_content["snapshot"]


async def test_right_click_updates_status_label(mcp_client: Client) -> None:
    result = await mcp_client.call_tool("right_click", {"locator": {"name": "ClickPad"}})
    assert "right-clicked" in result.structured_content["snapshot"]


async def test_fill_writes_text_and_emits_changed(mcp_client: Client) -> None:
    result = await mcp_client.call_tool(
        "fill", {"locator": {"name": "NameInput"}, "text": "Sanito"}
    )
    text = result.structured_content["snapshot"]
    # CharCounter listens on text_changed; "6/20" proves the signal fired.
    # LineEdit content is now in the positional `"text"` slot, not an attr.
    assert '"Sanito"' in text
    assert "6/20" in text


async def test_interaction_response_carries_tree_version(mcp_client: Client) -> None:
    """Interactions bundle their own fresh snapshot — no follow-up call needed."""
    first = await mcp_client.call_tool("click", {"locator": {"name": "Submit"}})
    second = await mcp_client.call_tool("click", {"locator": {"name": "Submit"}})
    assert first.structured_content["mode"] == "full"
    assert second.structured_content["tree_version"] > first.structured_content["tree_version"]


async def test_unknown_locator_raises_tool_error(mcp_client: Client) -> None:
    with pytest.raises(ToolError) as exc:
        await mcp_client.call_tool("click", {"locator": {"name": "NoSuchNode"}})
    assert "no matches" in str(exc.value).lower()


async def test_text_locator(mcp_client: Client) -> None:
    result = await mcp_client.call_tool("click", {"locator": {"text": "Submit"}})
    assert "submitted: " in result.structured_content["snapshot"]


async def test_describe_returns_dict(mcp_client: Client) -> None:
    result = await mcp_client.call_tool("describe", {"locator": {"name": "Counter"}})
    info = result.structured_content
    assert info["class"] == "CharCounter"
    assert info["custom_format"]["text"] == "0/20"
    assert info["custom_format"]["attrs"]["max"] == 20


async def test_wait_for_text_contains(mcp_client: Client) -> None:
    await mcp_client.call_tool("click", {"locator": {"name": "Submit"}})
    result = await mcp_client.call_tool(
        "wait_for",
        {"locator": {"name": "Status"}, "text_contains": "submitted"},
    )
    assert "submitted: " in result.structured_content["snapshot"]


async def test_wait_for_times_out(mcp_client: Client) -> None:
    with pytest.raises(ToolError) as exc:
        await mcp_client.call_tool(
            "wait_for",
            {
                "locator": {"name": "Status"},
                "text": "never-happens",
                "timeout_ms": 150,
            },
        )
    assert "timeout" in str(exc.value).lower()
