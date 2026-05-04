"""`screenshot` — capture the viewport (or a target Control) as PNG/JPEG."""

from __future__ import annotations

import base64
import datetime
import sys
from pathlib import Path

import click

from .. import output
from ..runner import coro_command, with_session


def _default_filename(fmt: str) -> str:
    ts = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    return f"screenshot-{ts}.{fmt}"


@click.command("screenshot")
@click.argument("ref", required=False, default=None)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["png", "jpeg"]),
    default="png",
    help="Output format (default: png).",
)
@click.option(
    "--filename",
    default=None,
    help="File name to save to. Defaults to `screenshot-{timestamp}.{png|jpeg}`.",
)
@click.option("--json", "as_json", is_flag=True, help="Emit `{filename}` as JSON.")
@click.pass_context
@coro_command
async def screenshot_cmd(
    ctx: click.Context,
    ref: str | None,
    fmt: str,
    filename: str | None,
    as_json: bool,
) -> None:
    """Capture a screenshot of the running game viewport.

    REF is an optional node reference (e.g. `e5`); when given, crops to that
    Control's global rect.
    """
    name_flag = ctx.obj.get("session") if ctx.obj else None
    params: dict[str, str] = {"format": fmt}
    if ref:
        params["ref"] = ref
    async with with_session(name_flag) as (_, client):
        result = await client.call("screenshot", **params)
    if not isinstance(result, dict) or "data" not in result:
        output.emit_error("error: screenshot returned no data")
        sys.exit(1)
    path = Path(filename) if filename else Path(_default_filename(fmt))
    path.write_bytes(base64.b64decode(result["data"]))
    if as_json:
        output.emit_json({"filename": str(path)})
        return
    output.emit(str(path))
