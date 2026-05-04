"""`eval` — run a single GDScript expression in the running game.

Gated on the addon side by `GODOT_LOCATOR_EVAL_ENABLED=true` — eval has full
expression-level access to game state, so it must be opted into per process.
"""

from __future__ import annotations

import json

import click

from .. import output
from ..runner import coro_command, with_session


@click.command("eval")
@click.argument("expression")
@click.option("--ref", default=None, help="Bind this node as the local variable `node`.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def eval_cmd(
    ctx: click.Context,
    expression: str,
    ref: str | None,
    as_json: bool,
) -> None:
    """Evaluate a GDScript expression in the running game.

    GDScript syntax — on C# projects use `node.get_name()`, not
    `node.GetName()`. Single-expression only (no `var`/`func`/multi-line).
    Requires `GODOT_LOCATOR_EVAL_ENABLED=true` on the game process.
    """
    name_flag = ctx.obj.get("session") if ctx.obj else None
    params: dict[str, str] = {"expression": expression}
    if ref:
        params["ref"] = ref
    async with with_session(name_flag) as (_, client):
        result = await client.call("evaluate", **params)
    if as_json:
        output.emit_json(result)
        return
    value = result.get("value") if isinstance(result, dict) else result
    if isinstance(value, (dict, list)):
        output.emit(json.dumps(value, default=str))
    else:
        output.emit(str(value))
