"""Output formatting. Default text mode keeps it dense (no banners, no
decorations) so AI agents reading the output spend few tokens on chrome.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import click

from godot_locator_core import Session


def emit_json(payload: Any) -> None:
    click.echo(json.dumps(payload, indent=2, default=str))


def emit_error(message: str) -> None:
    click.echo(message, err=True)


def render_context(session: Session, tree_version: int | None = None) -> str:
    lines = [
        "### Context",
        f"session: {session.name}",
        f"endpoint: {session.endpoint}",
    ]
    if tree_version is not None:
        lines.append(f"tree_version: {tree_version}")
    return "\n".join(lines)


def render_snapshot(snapshot: str) -> str:
    return "### Snapshot\n" + (snapshot.rstrip() if snapshot else "")


def render_interaction(
    session: Session,
    result: dict | None,
    *,
    show_snapshot: bool = True,
) -> str:
    """Format the bundled interaction response (`{snapshot, tree_version, mode}`)."""
    blocks: list[str] = []
    tree_version = result.get("tree_version") if result else None
    blocks.append(render_context(session, tree_version=tree_version))
    if show_snapshot and result and result.get("snapshot"):
        blocks.append(render_snapshot(result["snapshot"]))
    return "\n\n".join(blocks)


def emit(text: str) -> None:
    click.echo(text)


def is_tty() -> bool:
    return sys.stdout.isatty()
