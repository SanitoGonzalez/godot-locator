"""`sessions list` and `sessions rm` subcommands. `list` TCP-probes each
endpoint to flag live/stale without opening a real WebSocket."""

from __future__ import annotations

import asyncio
import socket
from urllib.parse import urlparse

import click

from godot_locator_core import (
    DEFAULT_NAME,
    Session,
    SessionStore,
    resolve_session_name,
)

from .. import output


@click.group("sessions")
def sessions_group() -> None:
    """Manage saved sessions."""


def _probe(session: Session, timeout: float = 0.3) -> str:
    """Quick TCP probe of the session's endpoint. Returns 'live' or 'stale'."""
    parsed = urlparse(session.endpoint)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8282
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return "live"
    except OSError:
        return "stale"


@sessions_group.command("list")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
def list_cmd(as_json: bool) -> None:
    """Show all sessions with live/stale status."""
    store = SessionStore()
    items = store.list()
    active = resolve_session_name(None)

    rows = []
    for s in items:
        rows.append(
            {
                "name": s.name,
                "endpoint": s.endpoint,
                "created_at": s.created_at,
                "pid": s.pid,
                "status": _probe(s),
                "active": s.name == active,
            }
        )

    if as_json:
        output.emit_json(rows)
        return

    if not rows:
        output.emit("(no sessions)")
        return

    width = max(len(r["name"]) for r in rows)
    for r in rows:
        marker = "*" if r["active"] else " "
        output.emit(
            f"{marker} {r['name']:<{width}}  {r['endpoint']:<28}  {r['status']:<5}  {r['created_at']}"
        )


@sessions_group.command("rm")
@click.argument("name")
def rm_cmd(name: str) -> None:
    """Delete a session file."""
    store = SessionStore()
    removed = store.delete(name)
    if not removed:
        output.emit_error(f"no session named '{name}'")
        raise click.exceptions.Exit(1)
    output.emit(f"removed session '{name}'")
