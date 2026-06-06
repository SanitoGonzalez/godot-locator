"""`assert` and `wait` — poll a condition against the live SceneTree.

Both drive the plugin's `assert` wire method, which re-resolves the target and
re-checks the matcher every frame until it passes or the timeout elapses. Exit
0 on pass, 1 on fail — so agents branch on the exit code. A failing assertion
prints the current snapshot so the agent can see why.
"""

from __future__ import annotations

import click

from .. import output
from ..runner import coro_command, with_session

# Matchers grouped by how many positional values they consume after MATCHER.
_NOARG = {"visible", "hidden", "exists", "absent", "checked", "unchecked", "enabled", "disabled"}
_ONEARG = {"text", "contains", "value", "count"}
_KV = {"property"}
_EXPR = {"expr"}
_ALL = sorted(_NOARG | _ONEARG | _KV | _EXPR)


def _build_params(target: str, matcher: str, expected: tuple[str, ...], timeout: float) -> dict[str, object]:
    params: dict[str, object] = {"target": target, "matcher": matcher, "timeout_ms": int(timeout * 1000)}
    if matcher in _NOARG:
        if expected:
            raise click.BadParameter(f"matcher '{matcher}' takes no value")
    elif matcher in _KV:
        if len(expected) != 2:
            raise click.BadParameter("matcher 'property' takes KEY and VALUE")
        params["key"] = expected[0]
        params["expected"] = expected[1]
    else:  # _ONEARG or _EXPR — join so quoted multi-word values/expressions survive
        if not expected:
            raise click.BadParameter(f"matcher '{matcher}' requires a value")
        params["expected"] = " ".join(expected)
    return params


def _emit(result: object, target: str, matcher: str, expected: tuple[str, ...], as_json: bool) -> None:
    if as_json:
        output.emit_json(result)
    else:
        passed = bool(result.get("pass")) if isinstance(result, dict) else False
        observed = result.get("observed") if isinstance(result, dict) else None
        waited = result.get("waited_ms") if isinstance(result, dict) else None
        cond = " ".join([matcher, *expected]).strip()
        if passed:
            output.emit(f"PASS  {target} {cond}")
        else:
            output.emit(f"FAIL  {target} {cond}  (observed: {observed}, waited {waited}ms)")
            snap = output.render_snapshot_block(result.get("snapshot") if isinstance(result, dict) else None)
            if snap:
                output.emit(snap)
    if not (isinstance(result, dict) and result.get("pass")):
        raise click.exceptions.Exit(1)


_MATCHER_ARG = click.argument("matcher", type=click.Choice(_ALL))
_EXPECTED_ARG = click.argument("expected", nargs=-1)


@click.command("assert")
@click.argument("target", metavar="TARGET")
@_MATCHER_ARG
@_EXPECTED_ARG
@click.option("--timeout", type=float, default=5.0, show_default=True, help="Seconds to keep polling before failing.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def assert_cmd(
    ctx: click.Context,
    target: str,
    matcher: str,
    expected: tuple[str, ...],
    timeout: float,
    as_json: bool,
) -> None:
    """Assert a condition on TARGET, polling until it holds or --timeout passes.

    TARGET is a ref (e.g. `e5`) or selector (`#Start`, `Button#Start`,
    `Label:text("Score")`, `/root/Game/Player`). MATCHER is one of: visible,
    hidden, exists, absent, checked, unchecked, enabled, disabled, text <s>,
    contains <s>, value <s>, count <n>, property <key> <value>, expr <gdscript>.

    For `expr`, TARGET binds as the local `node` (pass `-` for none); requires
    `GODOT_LOCATOR_EVAL_ENABLED=true`. Exits 1 on failure.
    """
    name_flag = ctx.obj.get("session") if ctx.obj else None
    params = _build_params(target, matcher, expected, timeout)
    async with with_session(name_flag) as (_, client):
        result = await client.call("assert", **params)
    _emit(result, target, matcher, expected, as_json)


@click.command("wait")
@click.argument("target", metavar="TARGET")
@click.argument("matcher", type=click.Choice(_ALL), default="visible", required=False)
@_EXPECTED_ARG
@click.option("--timeout", type=float, default=10.0, show_default=True, help="Seconds to keep polling before failing.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON.")
@click.pass_context
@coro_command
async def wait_cmd(
    ctx: click.Context,
    target: str,
    matcher: str,
    expected: tuple[str, ...],
    timeout: float,
    as_json: bool,
) -> None:
    """Wait for a condition on TARGET (default matcher: `visible`).

    Sugar for `assert` with a longer default timeout — same TARGET and MATCHER
    grammar. Exits 1 if the condition never holds within --timeout.
    """
    name_flag = ctx.obj.get("session") if ctx.obj else None
    params = _build_params(target, matcher, expected, timeout)
    async with with_session(name_flag) as (_, client):
        result = await client.call("assert", **params)
    _emit(result, target, matcher, expected, as_json)
