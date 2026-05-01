"""`attach` and `detach` — connect to / forget an already-running game."""

from __future__ import annotations

import socket
from urllib.parse import urlparse

import click

from godot_locator_core import (
    Session,
    SessionStore,
    resolve_session_name,
)
from godot_locator_core.errors import SessionNotFoundError

from .. import output


def _probe(endpoint: str, timeout: float = 1.0) -> bool:
    parsed = urlparse(endpoint)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8282
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@click.command("attach")
@click.option("--endpoint", required=True, help="WebSocket URL of the running game (e.g. ws://localhost:8282).")
@click.option("--no-probe", is_flag=True, help="Skip the reachability check.")
@click.pass_context
def attach_cmd(ctx: click.Context, endpoint: str, no_probe: bool) -> None:
    """Connect to an already-running game and save a session."""
    name_flag = ctx.obj.get("session") if ctx.obj else None
    name = resolve_session_name(name_flag)

    if not no_probe and not _probe(endpoint):
        output.emit_error(f"endpoint {endpoint} is not reachable — is your Godot game running?")
        raise click.exceptions.Exit(1)

    session = Session(name=name, endpoint=endpoint)
    SessionStore().save(session)
    output.emit(f"attached to {endpoint} as session '{name}'")


@click.command("detach")
@click.pass_context
def detach_cmd(ctx: click.Context) -> None:
    """Remove the current session (alias for `sessions rm <active>`)."""
    name_flag = ctx.obj.get("session") if ctx.obj else None
    name = resolve_session_name(name_flag)
    store = SessionStore()
    try:
        store.get(name)
    except SessionNotFoundError as e:
        output.emit_error(str(e))
        raise click.exceptions.Exit(1) from e
    store.delete(name)
    output.emit(f"detached from session '{name}'")
