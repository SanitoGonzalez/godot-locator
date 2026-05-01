"""Interaction commands: `click`, `type`, `wait_for`. Default text output
embeds the post-interaction snapshot so agents skip a follow-up `snapshot`."""

from __future__ import annotations

import click

from .. import output
from ..runner import coro_command, with_session


def _ref_locator(ref: str) -> dict:
    return {"ref": ref}


@click.command("click")
@click.argument("ref")
@click.option("--button", type=click.Choice(["left", "right", "middle"]), default="left", show_default=True)
@click.option("--double", is_flag=True, help="Double-click instead of single.")
@click.option("--no-snapshot", is_flag=True, help="Suppress the snapshot block.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def click_cmd(
    ctx: click.Context,
    ref: str,
    button: str,
    double: bool,
    no_snapshot: bool,
    as_json: bool,
) -> None:
    """Click a node by ref."""
    name_flag = ctx.obj.get("session") if ctx.obj else None
    if double:
        method = "double_click"
    elif button == "right":
        method = "right_click"
    else:
        method = "click"
    async with with_session(name_flag) as (session, client):
        result = await client.call(method, locator=_ref_locator(ref))
    if as_json:
        output.emit_json(result)
        return
    output.emit(output.render_interaction(session, result, show_snapshot=not no_snapshot))


@click.command("type")
@click.argument("ref")
@click.argument("text")
@click.option("--no-snapshot", is_flag=True, help="Suppress the snapshot block.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def type_cmd(
    ctx: click.Context,
    ref: str,
    text: str,
    no_snapshot: bool,
    as_json: bool,
) -> None:
    """Replace the text of a LineEdit/TextEdit by ref."""
    name_flag = ctx.obj.get("session") if ctx.obj else None
    async with with_session(name_flag) as (session, client):
        result = await client.call("fill", locator=_ref_locator(ref), text=text)
    if as_json:
        output.emit_json(result)
        return
    output.emit(output.render_interaction(session, result, show_snapshot=not no_snapshot))


@click.command("wait-for")
@click.argument("ref")
@click.option("--text", default=None, help="Match exactly on text.")
@click.option("--text-contains", default=None, help="Match on substring.")
@click.option("--count", type=int, default=None, help="Match exact match count.")
@click.option("--exists", is_flag=True, help="Match when at least one node matches.")
@click.option("--missing", is_flag=True, help="Match when zero nodes match.")
@click.option("--timeout-ms", type=int, default=2000, show_default=True)
@click.option("--interval-ms", type=int, default=50, show_default=True)
@click.option("--no-snapshot", is_flag=True, help="Suppress the snapshot block.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def wait_for_cmd(
    ctx: click.Context,
    ref: str,
    text: str | None,
    text_contains: str | None,
    count: int | None,
    exists: bool,
    missing: bool,
    timeout_ms: int,
    interval_ms: int,
    no_snapshot: bool,
    as_json: bool,
) -> None:
    """Poll the locator until a predicate holds, or time out."""
    name_flag = ctx.obj.get("session") if ctx.obj else None
    params: dict = {
        "locator": _ref_locator(ref),
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
    async with with_session(name_flag) as (session, client):
        result = await client.call("wait_for", **params)
    if as_json:
        output.emit_json(result)
        return
    output.emit(output.render_interaction(session, result, show_snapshot=not no_snapshot))
