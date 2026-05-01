"""`snapshot` — render the current SceneTree."""

from __future__ import annotations

import click

from .. import output
from ..runner import coro_command, with_session


@click.command("snapshot")
@click.option("--target", default=None, help="Subtree root reference (e.g. e3).")
@click.option("--depth", type=int, default=None, help="Limit tree depth.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def snapshot_cmd(
    ctx: click.Context,
    target: str | None,
    depth: int | None,
    as_json: bool,
) -> None:
    """Capture an accessibility snapshot of the SceneTree."""
    name_flag = ctx.obj.get("session") if ctx.obj else None
    params = {k: v for k, v in {"target": target, "depth": depth}.items() if v is not None}
    async with with_session(name_flag) as (session, client):
        result = await client.call("snapshot", **params)
    if as_json:
        output.emit_json({"snapshot": result})
        return
    output.emit(output.render_context(session))
    output.emit("")
    output.emit(output.render_snapshot(result if isinstance(result, str) else ""))
