"""Interaction commands: `click`, `dblclick`, `fill`, `type`. Default text
output embeds the post-interaction snapshot so agents skip a follow-up
`snapshot`."""

from __future__ import annotations

import click

from .. import output
from ..runner import coro_command, with_session


_BUTTON_ARG = click.argument(
    "button",
    type=click.Choice(["left", "right", "middle"]),
    default="left",
    required=False,
)


@click.command("click")
@click.argument("ref", metavar="TARGET")
@_BUTTON_ARG
@click.option("--no-snapshot", is_flag=True, help="Suppress the snapshot block.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def click_cmd(
    ctx: click.Context,
    ref: str,
    button: str,
    no_snapshot: bool,
    as_json: bool,
) -> None:
    """Click a node by ref. BUTTON defaults to 'left'."""
    name_flag = ctx.obj.get("session") if ctx.obj else None
    async with with_session(name_flag) as (session, client):
        result = await client.call("click", target=ref, button=button)
    if as_json:
        output.emit_json(result)
        return
    output.emit(output.render_interaction(session, result, show_snapshot=not no_snapshot))


@click.command("hover")
@click.argument("ref", metavar="TARGET")
@click.option("--no-snapshot", is_flag=True, help="Suppress the snapshot block.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def hover_cmd(
    ctx: click.Context,
    ref: str,
    no_snapshot: bool,
    as_json: bool,
) -> None:
    """Hover the mouse over a node by ref."""
    name_flag = ctx.obj.get("session") if ctx.obj else None
    async with with_session(name_flag) as (session, client):
        result = await client.call("hover", target=ref)
    if as_json:
        output.emit_json(result)
        return
    output.emit(output.render_interaction(session, result, show_snapshot=not no_snapshot))


@click.command("dblclick")
@click.argument("ref", metavar="TARGET")
@_BUTTON_ARG
@click.option("--no-snapshot", is_flag=True, help="Suppress the snapshot block.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def dblclick_cmd(
    ctx: click.Context,
    ref: str,
    button: str,
    no_snapshot: bool,
    as_json: bool,
) -> None:
    """Double-click a node by ref. BUTTON defaults to 'left'."""
    name_flag = ctx.obj.get("session") if ctx.obj else None
    async with with_session(name_flag) as (session, client):
        result = await client.call("double_click", target=ref, button=button)
    if as_json:
        output.emit_json(result)
        return
    output.emit(output.render_interaction(session, result, show_snapshot=not no_snapshot))


@click.command("fill")
@click.argument("ref", metavar="TARGET")
@click.argument("text")
@click.option("--no-snapshot", is_flag=True, help="Suppress the snapshot block.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def fill_cmd(
    ctx: click.Context,
    ref: str,
    text: str,
    no_snapshot: bool,
    as_json: bool,
) -> None:
    """Replace the text of a LineEdit/TextEdit by ref (atomic)."""
    name_flag = ctx.obj.get("session") if ctx.obj else None
    async with with_session(name_flag) as (session, client):
        result = await client.call("fill", target=ref, text=text)
    if as_json:
        output.emit_json(result)
        return
    output.emit(output.render_interaction(session, result, show_snapshot=not no_snapshot))


@click.command("check")
@click.argument("ref", metavar="TARGET")
@click.option("--no-snapshot", is_flag=True, help="Suppress the snapshot block.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def check_cmd(
    ctx: click.Context,
    ref: str,
    no_snapshot: bool,
    as_json: bool,
) -> None:
    """Set a toggle-mode button (CheckBox/CheckButton) to checked."""
    name_flag = ctx.obj.get("session") if ctx.obj else None
    async with with_session(name_flag) as (session, client):
        result = await client.call("check", target=ref)
    if as_json:
        output.emit_json(result)
        return
    output.emit(output.render_interaction(session, result, show_snapshot=not no_snapshot))


@click.command("uncheck")
@click.argument("ref", metavar="TARGET")
@click.option("--no-snapshot", is_flag=True, help="Suppress the snapshot block.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def uncheck_cmd(
    ctx: click.Context,
    ref: str,
    no_snapshot: bool,
    as_json: bool,
) -> None:
    """Set a toggle-mode button (CheckBox/CheckButton) to unchecked."""
    name_flag = ctx.obj.get("session") if ctx.obj else None
    async with with_session(name_flag) as (session, client):
        result = await client.call("uncheck", target=ref)
    if as_json:
        output.emit_json(result)
        return
    output.emit(output.render_interaction(session, result, show_snapshot=not no_snapshot))


@click.command("select")
@click.argument("ref", metavar="TARGET")
@click.argument("value")
@click.option("--no-snapshot", is_flag=True, help="Suppress the snapshot block.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def select_cmd(
    ctx: click.Context,
    ref: str,
    value: str,
    no_snapshot: bool,
    as_json: bool,
) -> None:
    """Select an OptionButton item by index or label."""
    name_flag = ctx.obj.get("session") if ctx.obj else None
    async with with_session(name_flag) as (session, client):
        result = await client.call("select", target=ref, value=value)
    if as_json:
        output.emit_json(result)
        return
    output.emit(output.render_interaction(session, result, show_snapshot=not no_snapshot))


@click.command("type")
@click.argument("text")
@click.option("--no-snapshot", is_flag=True, help="Suppress the snapshot block.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def type_cmd(
    ctx: click.Context,
    text: str,
    no_snapshot: bool,
    as_json: bool,
) -> None:
    """Type text into the currently focused Control (per-character key events)."""
    name_flag = ctx.obj.get("session") if ctx.obj else None
    async with with_session(name_flag) as (session, client):
        result = await client.call("type", text=text)
    if as_json:
        output.emit_json(result)
        return
    output.emit(output.render_interaction(session, result, show_snapshot=not no_snapshot))


@click.command("press")
@click.argument("key")
@click.option("--no-snapshot", is_flag=True, help="Suppress the snapshot block.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def press_cmd(
    ctx: click.Context,
    key: str,
    no_snapshot: bool,
    as_json: bool,
) -> None:
    """Press a single key (e.g. `enter`, `escape`, `arrowleft`, `f1`, `a`).

    Synthesizes a keyboard press+release. For typing text, prefer `fill` or
    `type`. For game-logic-level inputs that should match what the player
    does (and respect keyboard/gamepad mappings), use `action` instead.
    """
    name_flag = ctx.obj.get("session") if ctx.obj else None
    async with with_session(name_flag) as (session, client):
        result = await client.call("press", key=key)
    if as_json:
        output.emit_json(result)
        return
    output.emit(output.render_interaction(session, result, show_snapshot=not no_snapshot))


@click.command("keydown")
@click.argument("key")
@click.option("--no-snapshot", is_flag=True, help="Suppress the snapshot block.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def keydown_cmd(
    ctx: click.Context,
    key: str,
    no_snapshot: bool,
    as_json: bool,
) -> None:
    """Press a key down without releasing it. Use `keyup` to release.

    Use when you need a key held across multiple frames (e.g. testing held
    movement keys, character autorepeat). For tap-style press+release, use
    `press`. KEY accepts the same names as `press` (`enter`, `arrowleft`,
    `f1`, `a`).
    """
    name_flag = ctx.obj.get("session") if ctx.obj else None
    async with with_session(name_flag) as (session, client):
        result = await client.call("keydown", key=key)
    if as_json:
        output.emit_json(result)
        return
    output.emit(output.render_interaction(session, result, show_snapshot=not no_snapshot))


@click.command("keyup")
@click.argument("key")
@click.option("--no-snapshot", is_flag=True, help="Suppress the snapshot block.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def keyup_cmd(
    ctx: click.Context,
    key: str,
    no_snapshot: bool,
    as_json: bool,
) -> None:
    """Release a key previously held with `keydown`."""
    name_flag = ctx.obj.get("session") if ctx.obj else None
    async with with_session(name_flag) as (session, client):
        result = await client.call("keyup", key=key)
    if as_json:
        output.emit_json(result)
        return
    output.emit(output.render_interaction(session, result, show_snapshot=not no_snapshot))


@click.command("mousemove")
@click.argument("x", type=float)
@click.argument("y", type=float)
@click.option("--no-snapshot", is_flag=True, help="Suppress the snapshot block.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def mousemove_cmd(
    ctx: click.Context,
    x: float,
    y: float,
    no_snapshot: bool,
    as_json: bool,
) -> None:
    """Move the cursor to viewport coordinates (X, Y).

    Synthesizes an `InputEventMouseMotion` and remembers the position for
    later `mousedown`/`mouseup` calls.
    """
    name_flag = ctx.obj.get("session") if ctx.obj else None
    async with with_session(name_flag) as (session, client):
        result = await client.call("mousemove", x=x, y=y)
    if as_json:
        output.emit_json(result)
        return
    output.emit(output.render_interaction(session, result, show_snapshot=not no_snapshot))


@click.command("mousedown")
@_BUTTON_ARG
@click.option("--no-snapshot", is_flag=True, help="Suppress the snapshot block.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def mousedown_cmd(
    ctx: click.Context,
    button: str,
    no_snapshot: bool,
    as_json: bool,
) -> None:
    """Press a mouse button at the current cursor position. BUTTON defaults to 'left'.

    Use `mousemove` first to position the cursor. Lets tests held-drag
    (mousedown -> mousemove(s) -> mouseup) without triggering Godot's
    auto drag detection.
    """
    name_flag = ctx.obj.get("session") if ctx.obj else None
    async with with_session(name_flag) as (session, client):
        result = await client.call("mousedown", button=button)
    if as_json:
        output.emit_json(result)
        return
    output.emit(output.render_interaction(session, result, show_snapshot=not no_snapshot))


@click.command("mouseup")
@_BUTTON_ARG
@click.option("--no-snapshot", is_flag=True, help="Suppress the snapshot block.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def mouseup_cmd(
    ctx: click.Context,
    button: str,
    no_snapshot: bool,
    as_json: bool,
) -> None:
    """Release a mouse button at the current cursor position. BUTTON defaults to 'left'."""
    name_flag = ctx.obj.get("session") if ctx.obj else None
    async with with_session(name_flag) as (session, client):
        result = await client.call("mouseup", button=button)
    if as_json:
        output.emit_json(result)
        return
    output.emit(output.render_interaction(session, result, show_snapshot=not no_snapshot))


@click.command("mousewheel")
@click.argument("dx", type=int)
@click.argument("dy", type=int)
@click.option("--ref", default=None, help="Optional node ref; else viewport center.")
@click.option("--no-snapshot", is_flag=True, help="Suppress the snapshot block.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def mousewheel_cmd(
    ctx: click.Context,
    dx: int,
    dy: int,
    ref: str | None,
    no_snapshot: bool,
    as_json: bool,
) -> None:
    """Scroll the mouse wheel. DX/DY are tick counts (positive = right/down).

    Each tick is one press+release pair of `MOUSE_BUTTON_WHEEL_*`. With
    `--ref`, the wheel event fires at that node's center; otherwise at the
    viewport center, so it routes to whatever Control sits under that point.
    """
    name_flag = ctx.obj.get("session") if ctx.obj else None
    params: dict[str, object] = {"dx": dx, "dy": dy}
    if ref:
        params["ref"] = ref
    async with with_session(name_flag) as (session, client):
        result = await client.call("mousewheel", **params)
    if as_json:
        output.emit_json(result)
        return
    output.emit(output.render_interaction(session, result, show_snapshot=not no_snapshot))


@click.command("drag")
@click.argument("from_ref", metavar="FROM_REF")
@click.argument("to_ref", metavar="TO_REF")
@_BUTTON_ARG
@click.option("--no-snapshot", is_flag=True, help="Suppress the snapshot block.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def drag_cmd(
    ctx: click.Context,
    from_ref: str,
    to_ref: str,
    button: str,
    no_snapshot: bool,
    as_json: bool,
) -> None:
    """Drag from one node ref to another. BUTTON defaults to 'left'.

    Synthesizes a button-down at FROM_REF, several motion events stepping
    toward TO_REF (so Godot's drag-detect threshold trips and
    `_get_drag_data` is invoked), then a button-up at TO_REF.
    """
    name_flag = ctx.obj.get("session") if ctx.obj else None
    async with with_session(name_flag) as (session, client):
        result = await client.call("drag", **{"from": from_ref, "to": to_ref, "button": button})
    if as_json:
        output.emit_json(result)
        return
    output.emit(output.render_interaction(session, result, show_snapshot=not no_snapshot))


@click.command("resize")
@click.argument("width", type=int)
@click.argument("height", type=int)
@click.option("--no-snapshot", is_flag=True, help="Suppress the snapshot block.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def resize_cmd(
    ctx: click.Context,
    width: int,
    height: int,
    no_snapshot: bool,
    as_json: bool,
) -> None:
    """Resize the game window to WIDTH x HEIGHT pixels."""
    name_flag = ctx.obj.get("session") if ctx.obj else None
    async with with_session(name_flag) as (session, client):
        result = await client.call("resize", width=width, height=height)
    if as_json:
        output.emit_json(result)
        return
    output.emit(output.render_interaction(session, result, show_snapshot=not no_snapshot))


_ACTION_MODE_ARG = click.argument(
    "mode",
    type=click.Choice(["tap", "hold", "release"]),
    default="tap",
    required=False,
)


@click.command("action")
@click.argument("name")
@_ACTION_MODE_ARG
@click.option("--no-snapshot", is_flag=True, help="Suppress the snapshot block.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def action_cmd(
    ctx: click.Context,
    name: str,
    mode: str,
    no_snapshot: bool,
    as_json: bool,
) -> None:
    """Drive a Godot input action by name. MODE defaults to 'tap'.

    `tap` presses then releases (most common — `is_action_just_pressed`
    will fire). `hold` presses without releasing — use for sustained
    inputs. `release` releases a previously-held action. NAME must be a
    registered action in Project Settings → Input Map.
    """
    name_flag = ctx.obj.get("session") if ctx.obj else None
    async with with_session(name_flag) as (session, client):
        result = await client.call("action", name=name, mode=mode)
    if as_json:
        output.emit_json(result)
        return
    output.emit(output.render_interaction(session, result, show_snapshot=not no_snapshot))
