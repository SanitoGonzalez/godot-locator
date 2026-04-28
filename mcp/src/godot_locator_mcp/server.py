"""FastMCP server exposing godot-locator's runtime methods as MCP tools.

Each ``@mcp.tool`` mirrors one wire method. We only surface methods that the
Godot side has actually implemented — stubs are omitted on purpose so the
model doesn't waste turns calling no-ops.

Refs only exist after a snapshot taken with ``tag_ref=true`` (the default at
the MCP layer); they're stable for the lifetime of the running game.

Environment variables
---------------------
GODOT_LOCATOR_HOST            IP of the running Godot game (default 127.0.0.1).
GODOT_LOCATOR_PORT            TCP port (default 8282).
GODOT_LOCATOR_MCP_CAPABILITIES  Comma-separated capability tags (same as --capabilities).
GODOT_LOCATOR_MCP_SNAPSHOT_MODE Snapshot mode for interaction responses (same as --snapshot-mode).
"""

from __future__ import annotations

import argparse
import os
from typing import Annotated, Any, TypedDict

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from .client import LocatorClient, LocatorError

mcp: FastMCP = FastMCP(
    "Godot Locator MCP",
    instructions="Provides Playwright-style tools for interacting with Godot Engine based runtimes. Start with `snapshot()` for the current state.",
)


class InteractionResult(TypedDict):
    """Bundled post-interaction state — saves a follow-up `snapshot` round-trip.

    `snapshot` is the tree as of just after the interaction ran. `tree_version`
    is a monotonic counter for drift detection across turns. `mode` is `"full"`
    today; future delta encoding will add `"delta"`.
    """

    snapshot: str
    tree_version: int
    mode: str

_client: LocatorClient | None = None
_snapshot_mode: str = "full"


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


def _apply_snapshot_mode(result: InteractionResult) -> InteractionResult:
    if _snapshot_mode == "none":
        return {"snapshot": "", "tree_version": result["tree_version"], "mode": "none"}
    return result


async def _call(method: str, **params: Any) -> Any:
    try:
        return await _get_client().call(method, **params)
    except LocatorError as e:
        raise ToolError(str(e)) from e


NodeReference = Annotated[str, Field(description="UI Node reference from snapshot.")]
Button = Annotated[str, Field(description='"left" (default), "right", or "middle"')]


@mcp.tool(
    tags={"core"},
    annotations={"readOnlyHint": True},
)
async def snapshot(
    target: Annotated[NodeReference | None, Field(description="Exact target node reference to be root of the snapshot tree")] = None,
    depth: Annotated[int | None, Field(description="Limit the depth of the snapshot tree")] = None,
) -> str:
    """Capture accessibility snapshot of SceneTree"""
    params = {k: v for k, v in {"target": target, "depth": depth}.items() if v is not None}
    return await _call("snapshot", **params)

@mcp.tool(
    tags={"core"},
    annotations={"readOnlyHint": True},
)
async def screenshot(
    target: Annotated[NodeReference | None, Field(description="Exact target node reference")] = None,
    type: Annotated[str, Field(description='"png" (default), or "jpeg"')] = "png",
) -> str:
    """Take a screenshot of the app"""
    ...

@mcp.tool(tags={"core"})
async def evaluate(
    expression: Annotated[str, Field(description="{code} or {var node = <target>; code} when target is provided")],
    target: Annotated[NodeReference | None, Field(description="Exact target node reference")] = None,
) -> str:
    """Evaluate GDScript expression on scene or node"""
    ...

@mcp.tool(tags={"core"})
async def click(
    ref: NodeReference,
    doubleClick: bool = False,
    button: Button = "left",
) -> InteractionResult:
    """Click an UI node in the SceneTree."""
    return _apply_snapshot_mode(await _call("click", ref=ref))


@mcp.tool(name="type", tags={"core"})
async def type_(
    ref: NodeReference,
    text: Annotated[str, Field(description="Replacement text. The field is cleared, then set; `text_changed` is emitted.")],
) -> InteractionResult:
    """Replace the text of a LineEdit / TextEdit. Errors on other node types.

    Returns the bundled post-interaction state — see `click` for the response shape.
    """
    return _apply_snapshot_mode(await _call("type", ref=ref, text=text))


@mcp.tool(tags={"core"})
async def wait_for(
    ref: NodeReference,
    text: Annotated[str | None, Field(
        default=None,
        description="Match exactly when the resolved node's text equals this.",
    )] = None,
    text_contains: Annotated[str | None, Field(
        default=None,
        description="Match when the resolved node's text contains this substring.",
    )] = None,
    count: Annotated[int | None, Field(
        default=None,
        description="Match when there are exactly this many locator matches.",
    )] = None,
    exists: Annotated[bool, Field(
        default=False,
        description="Match when at least one node matches.",
    )] = False,
    missing: Annotated[bool, Field(
        default=False,
        description="Match when zero nodes match.",
    )] = False,
    timeout_ms: Annotated[int, Field(
        default=2000, ge=50,
        description="Give up after this many milliseconds.",
    )] = 2000,
    interval_ms: Annotated[int, Field(
        default=50, ge=10,
        description="Poll every this many milliseconds.",
    )] = 50,
) -> InteractionResult:
    """Poll the locator until a predicate holds, or time out.

    Use after an async interaction (signal, tween, network call) where the next
    snapshot might not yet reflect the new state. At least one of
    ``text`` / ``text_contains`` / ``count`` / ``exists`` / ``missing`` must
    be set; multiple conditions AND-combine. ``text`` and ``text_contains``
    only fire when the ref resolves to exactly one node.

    Returns the bundled post-condition state — see ``click`` for the response
    shape. Errors with ``wait_for: timeout ...`` if the condition isn't met
    in time.
    """
    params: dict[str, Any] = {
        "ref": ref,
        "timeout_ms": timeout_ms,
        "interval_ms": interval_ms,
    }
    if text is not None:
        params["text"] = text
    if text_contains is not None:
        params["text_contains"] = text_contains
    if count is not None:
        params["count"] = count
    if exists:
        params["exists"] = True
    if missing:
        params["missing"] = True
    return _apply_snapshot_mode(await _call("wait_for", **params))


@mcp.tool(tags={"mouse"})
async def mouse_move_xy(
    x: Annotated[int, Field(description="X coordinate")],
    y: Annotated[int, Field(description="Y coordinate")],
) -> None:
    """Move the mouse to specific coordinates."""
    ...


@mcp.tool(tags={"mouse"})
async def mouse_click_xy(
    x: Annotated[int, Field(description="X coordinate")],
    y: Annotated[int, Field(description="Y coordinate")],
    button: Annotated[str, Field(description='"left" (default), "right", or "middle"')] = "left",
    clickCount: Annotated[int, Field(ge=0, description="Number of clicks (2 for double-click)")] = 1,
    delay: Annotated[int, Field(description="Delay between mousedown and mouseup (ms)")] = 0,
) -> InteractionResult:
    """Click at specific coordinates without needing to move first."""
    ...


@mcp.tool(tags={"mouse"})
async def mouse_drag_xy(
    start_x: Annotated[int, Field(description="Start X coordinate")],
    start_y: Annotated[int, Field(description="Start Y coordinate")],
    end_x: Annotated[int, Field(description="End X coordinate")],
    end_y: Annotated[int, Field(description="End Y coordinate")],
) -> InteractionResult:
    """Drag the mouse from one position to another."""
    ...


@mcp.tool(tags={"mouse"})
async def mouse_down(
    button: Annotated[str, Field(description='"left" (default), "right", or "middle"')] = "left",
) -> None:
    """Press the mouse button at the current position."""
    ...


@mcp.tool(tags={"mouse"})
async def mouse_up(
    button: Annotated[str, Field(description='"left" (default), "right", or "middle"')] = "left",
) -> None:
    """Releaes the mouse button at the current position."""
    ...


@mcp.tool(tags={"mouse"})
async def mouse_wheel(
    delta_x: Annotated[int, Field(description="Horizontal scroll amount in pixels. Positive scrolls right.")] = 0,
    delta_y: Annotated[int, Field(description="Vertical scroll amount in pixels. Positive scrolls down.")] = 0,
) -> None:
    """Scroll the mouse wheel."""
    ...


def _csv_set(s: str) -> set[str]:
    return set(filter(None, s.split(",")))


def main() -> None:
    global _snapshot_mode
    parser = argparse.ArgumentParser(
        prog="godot-locator-mcp",
        description="MCP server bridging AI agents to a running Godot game.",
    )
    parser.add_argument(
        "--capabilities",
        type=_csv_set,
        default=_csv_set(os.environ.get("GODOT_LOCATOR_MCP_CAPABILITIES", "")),
        metavar="CAP,...",
        help="Comma-separated extra capability tags to enable (core is always on).",
    )
    parser.add_argument(
        "--snapshot-mode",
        choices=["full", "delta", "none"],
        default=os.environ.get("GODOT_LOCATOR_MCP_SNAPSHOT_MODE", "full"),
        dest="snapshot_mode",
        metavar="MODE",
        help=(
            "Snapshot payload in interaction responses: "
            '"full" (default) returns the full tree, '
            '"none" omits it, '
            '"delta" returns only changed nodes (reserved).'
        ),
    )
    args = parser.parse_args()
    _snapshot_mode = args.snapshot_mode
    mcp.enable(tags={"core"} | args.capabilities, only=True)
    mcp.run()


if __name__ == "__main__":
    main()
