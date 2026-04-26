"""FastMCP server exposing godot-locator's runtime methods as MCP tools.

Each ``@mcp.tool`` mirrors one wire method. We only surface methods that the
Godot side has actually implemented — stubs are omitted on purpose so the
model doesn't waste turns calling no-ops.

Locators are passed as plain dicts and are AND-matched on the Godot side:

    {"name": "Submit"}                 # match by node name
    {"class": "Button"}                # match by class (script name or engine)
    {"ref": "e3"}                      # match by ref id from a tagged snapshot
    {"name": "Submit", "class": "Button"}

Refs only exist after a snapshot taken with ``tag_ref=true`` (the default at
the MCP layer); they're stable for the lifetime of the running game.
"""

from __future__ import annotations

import os
from typing import Annotated, Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from .client import LocatorClient, LocatorError

mcp: FastMCP = FastMCP("godot-locator")

_client: LocatorClient | None = None


def _get_client() -> LocatorClient:
    global _client
    if _client is None:
        host = os.environ.get("GODOT_LOCATOR_HOST", "127.0.0.1")
        port = int(os.environ.get("GODOT_LOCATOR_PORT", "8282"))
        _client = LocatorClient(host=host, port=port)
    return _client


def _set_client(client: LocatorClient | None) -> None:
    """Test hook — swap the module-level client (or clear it)."""
    global _client
    _client = client


async def _call(method: str, **params: Any) -> Any:
    try:
        return await _get_client().call(method, **params)
    except LocatorError as e:
        raise ToolError(str(e)) from e


Locator = Annotated[
    dict[str, Any],
    Field(
        description=(
            "Locator dict — keys AND-match. Supported: "
            "`name` (node name), `class` (class/script name), `ref` (e.g. `e3`, "
            "from a tagged snapshot). Example: `{\"name\": \"Submit\"}`."
        ),
    ),
]


@mcp.tool
async def snapshot(
    depth: Annotated[int, Field(ge=0, description="Max traversal depth from the root. 0 = no limit.")] = 0,
    skip_invisible: Annotated[bool, Field(description="Omit nodes whose `visible` chain is false (and their subtrees).")] = True,
    tag_ref: Annotated[bool, Field(description="Emit `ref=eN` markers for interactive / custom-format nodes so later tool calls can target them.")] = True,
) -> str:
    """Render the running game's SceneTree as a YAML-style text snapshot.

    Lines look like ``- <Class> [<name>[ ref=eN]] ["<text>"] [<key>="<val>"]* [<flag>]*``.
    Only Control nodes are emitted; non-Control parents (Window, CanvasLayer,
    Node2D…) are walked through transparently. Use this to see the current UI
    before deciding what to click/fill.
    """
    return await _call("snapshot", depth=depth, skip_invisible=skip_invisible, tag_ref=tag_ref)


@mcp.tool
async def click(locator: Locator) -> None:
    """Synthesize a left-click at the center of the single node matching `locator`.

    Errors if zero or more than one node matches. Use a more specific locator
    (e.g. add `class` or `ref`) to disambiguate.
    """
    await _call("click", locator=locator)


@mcp.tool
async def double_click(locator: Locator) -> None:
    """Synthesize a left double-click on the single matching node."""
    await _call("double_click", locator=locator)


@mcp.tool
async def right_click(locator: Locator) -> None:
    """Synthesize a right-click on the single matching node."""
    await _call("right_click", locator=locator)


@mcp.tool
async def fill(
    locator: Locator,
    text: Annotated[str, Field(description="Replacement text. The field is cleared, then set; `text_changed` is emitted.")],
) -> None:
    """Replace the text of a LineEdit / TextEdit. Errors on other node types."""
    await _call("fill", locator=locator, text=text)
