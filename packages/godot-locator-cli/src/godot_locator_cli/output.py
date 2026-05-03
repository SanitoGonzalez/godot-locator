"""Output formatting. Default text mode keeps it dense (no banners, no
decorations) so AI agents reading the output spend few tokens on chrome.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import click

from godot_locator_core import Session, render_snapshot


def emit_json(payload: Any) -> None:
    click.echo(json.dumps(payload, indent=2, default=str))


def emit_error(message: str) -> None:
    click.echo(message, err=True)


def render_snapshot_block(snapshot: dict | None) -> str:
    return render_snapshot(snapshot) if snapshot else ""


def render_interaction(
    session: Session,
    result: dict | None,
    *,
    show_snapshot: bool = True,
) -> str:
    blocks: list[str] = []
    tree_version = result.get("tree_version") if result else None
    if show_snapshot and result:
        rendered = render_snapshot_block(result.get("snapshot"))
        if rendered:
            blocks.append(rendered)
    return "\n\n".join(blocks)


def emit(text: str) -> None:
    click.echo(text)


def is_tty() -> bool:
    return sys.stdout.isatty()
