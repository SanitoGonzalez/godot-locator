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
@click.argument("ref")
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
        result = await client.call("click", ref=ref, button=button)
    if as_json:
        output.emit_json(result)
        return
    output.emit(output.render_interaction(session, result, show_snapshot=not no_snapshot))


@click.command("dblclick")
@click.argument("ref")
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
        result = await client.call("double_click", ref=ref, button=button)
    if as_json:
        output.emit_json(result)
        return
    output.emit(output.render_interaction(session, result, show_snapshot=not no_snapshot))


@click.command("fill")
@click.argument("ref")
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
        result = await client.call("fill", ref=ref, text=text)
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
