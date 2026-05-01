"""`launch` and `terminate` — start/stop a Godot game and its session."""

from __future__ import annotations

from pathlib import Path

import click

from godot_locator_core import (
    Session,
    SessionStore,
    find_free_port,
    is_alive,
    launch as core_launch,
    resolve_session_name,
    terminate as core_terminate,
    wait_for_endpoint,
)
from godot_locator_core.errors import SessionNotFoundError

from .. import output


@click.command("launch")
@click.argument("project_path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--headed", is_flag=True, help="Launch with a visible window (default: headless).")
@click.option("--port", type=int, default=None, help="Bind the locator to this port (default: ephemeral).")
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind the locator to this host.")
@click.option("--timeout", type=float, default=10.0, show_default=True, help="Seconds to wait for the WebSocket.")
@click.pass_context
def launch_cmd(
    ctx: click.Context,
    project_path: Path,
    headed: bool,
    port: int | None,
    host: str,
    timeout: float,
) -> None:
    """Start a new Godot game and attach to it."""
    name_flag = ctx.obj.get("session") if ctx.obj else None
    name = resolve_session_name(name_flag)

    chosen_port = port if port is not None else find_free_port()
    proc = core_launch(project_path.resolve(), headed=headed, port=chosen_port, host=host)
    try:
        wait_for_endpoint(host, chosen_port, timeout_s=timeout)
    except TimeoutError as e:
        # Don't leak an orphaned headless Godot if it came up but never bound the port.
        core_terminate(proc.pid)
        output.emit_error(str(e))
        raise click.exceptions.Exit(1) from e

    session = Session(name=name, endpoint=proc.endpoint, pid=proc.pid)
    SessionStore().save(session)

    output.emit(f"launched godot (pid={proc.pid}) on {proc.endpoint}")
    output.emit(f"saved session '{name}'")


@click.command("terminate")
@click.pass_context
def terminate_cmd(ctx: click.Context) -> None:
    """Send shutdown to the game and remove the session."""
    name_flag = ctx.obj.get("session") if ctx.obj else None
    name = resolve_session_name(name_flag)
    store = SessionStore()
    try:
        session = store.get(name)
    except SessionNotFoundError as e:
        output.emit_error(str(e))
        raise click.exceptions.Exit(1) from e

    if session.pid is None:
        output.emit_error(
            f"session '{name}' was created via `attach` — use `detach` to remove it without killing the game."
        )
        raise click.exceptions.Exit(2)

    if is_alive(session.pid):
        core_terminate(session.pid)
        output.emit(f"sent SIGTERM to godot (pid={session.pid})")
    else:
        output.emit(f"godot (pid={session.pid}) already exited")

    store.delete(session.name)
    output.emit(f"removed session '{name}'")
