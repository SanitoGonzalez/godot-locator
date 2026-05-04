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

import base64

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import Image
from pydantic import Field

from godot_locator_core import LocatorClient, LocatorError, render_snapshot

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


def _apply_snapshot_mode(result: dict[str, Any]) -> InteractionResult:
    tree_version = int(result.get("tree_version", 0))
    if _snapshot_mode == "none":
        return {"snapshot": "", "tree_version": tree_version, "mode": "none"}
    return {
        "snapshot": render_snapshot(result.get("snapshot")),
        "tree_version": tree_version,
        "mode": str(result.get("mode", "full")),
    }


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
    return render_snapshot(await _call("snapshot", **params))

@mcp.tool(
    tags={"core"},
    annotations={"readOnlyHint": True},
)
async def screenshot(
    ref: Annotated[NodeReference | None, Field(description="Crop to this Control's global rect.")] = None,
    format: Annotated[str, Field(description='"png" (default) or "jpeg".')] = "png",
) -> Image:
    """Capture the running game's viewport as an image.

    Useful when the textual snapshot can't show what you need: custom-drawn
    nodes, sprites, particles, theme regressions, layout glitches.
    """
    params: dict[str, Any] = {"format": format}
    if ref:
        params["ref"] = ref
    result = await _call("screenshot", **params)
    if not isinstance(result, dict) or "data" not in result:
        raise ToolError("screenshot returned no data")
    return Image(data=base64.b64decode(result["data"]), format=result.get("format", format))


@mcp.tool(tags={"core"})
async def evaluate(
    expression: Annotated[str, Field(description="A single GDScript expression. When `ref` is set, `node` is bound to the resolved Node.")],
    ref: Annotated[NodeReference | None, Field(description="Bind this node as the local variable `node`.")] = None,
) -> Any:
    """Evaluate a GDScript expression in the running game.

    GDScript syntax — even on C# projects, use `node.get_name()`, not
    `node.GetName()`. Single-expression only (no `var`/`func`/multi-line).
    Requires `GODOT_LOCATOR_EVAL_ENABLED=true` on the game process.
    """
    params: dict[str, Any] = {"expression": expression}
    if ref:
        params["ref"] = ref
    result = await _call("evaluate", **params)
    if isinstance(result, dict) and "value" in result:
        return result["value"]
    return result

@mcp.tool(tags={"core"})
async def click(
    ref: NodeReference,
    doubleClick: bool = False,
    button: Button = "left",
) -> InteractionResult:
    """Click a UI node in the SceneTree."""
    method = "double_click" if doubleClick else "click"
    return _apply_snapshot_mode(await _call(method, ref=ref, button=button))


@mcp.tool(tags={"core"})
async def fill(
    ref: NodeReference,
    text: Annotated[str, Field(description="Replacement text. The field is cleared, then set; `text_changed` is emitted.")],
) -> InteractionResult:
    """Replace the text of a LineEdit / TextEdit by ref (atomic). Errors on other node types.

    Returns the bundled post-interaction state — see `click` for the response shape.
    """
    return _apply_snapshot_mode(await _call("fill", ref=ref, text=text))


@mcp.tool(name="type", tags={"core"})
async def type_(
    text: Annotated[str, Field(description="Text to type into the currently focused Control. One InputEventKey per character.")],
) -> InteractionResult:
    """Type into the currently focused Control via synthesized key events.

    Use when the game itself decides which control receives input (e.g. a
    chat box that's already focused). For atomic field replacement, use
    `fill` with a ref instead. Errors when no Control is focused.
    """
    return _apply_snapshot_mode(await _call("type", text=text))


@mcp.tool(tags={"core"})
async def press(
    key: Annotated[str, Field(description="Key name: 'enter', 'escape', 'arrowleft', 'f1', or single chars like 'a' / '1'.")],
) -> InteractionResult:
    """Press a single keyboard key (press + release).

    For typing text, use `fill` or `type`. For game-logic-level inputs that
    should respect the player's keyboard/gamepad mappings, use `action`.
    """
    return _apply_snapshot_mode(await _call("press", key=key))


@mcp.tool(tags={"core"})
async def action(
    name: Annotated[str, Field(description="Godot action name registered in Project Settings → Input Map.")],
    mode: Annotated[str, Field(description='"tap" (default; press+release), "hold" (press only), or "release".')] = "tap",
) -> InteractionResult:
    """Drive a Godot input action by name.

    Device-agnostic: the action fires regardless of whether the player
    bound it to keyboard, gamepad, or mouse. `tap` is the typical choice
    — `is_action_just_pressed` will see it. Use `hold`/`release` pairs
    for sustained inputs (e.g., walking).
    """
    return _apply_snapshot_mode(await _call("action", name=name, mode=mode))


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


def main():
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
