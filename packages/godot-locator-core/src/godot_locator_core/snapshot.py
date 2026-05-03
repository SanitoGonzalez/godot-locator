"""Render the Godot-side structured snapshot into the YAML-style text agents
see. The plugin returns ``{"tree": [...], "context"?: {...}}``; downstream
consumers (CLI, MCP) format it with the helpers here.
"""

from __future__ import annotations

from typing import Any


def render(snapshot: dict[str, Any] | None) -> str:
    """Render a snapshot dict to YAML-style text.

    Returns the empty string for falsy or malformed input. The ``context``
    block, when present, is emitted before the tree under a ``### Context``
    header; the tree itself is emitted under ``### Snapshot``.
    """
    if not isinstance(snapshot, dict):
        return ""
    blocks: list[str] = []
    context = snapshot.get("context")
    if isinstance(context, dict) and context:
        blocks.append(_render_context(context))
    tree = snapshot.get("tree")
    if isinstance(tree, list):
        blocks.append("### Snapshot\n" + _render_tree(tree))
    return "\n\n".join(blocks)


def _render_context(context: dict[str, Any]) -> str:
    lines = ["### Context"]
    for k, v in context.items():
        lines.append(f"{k}: {v}")
    return "\n".join(lines)


def _render_tree(tree: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for entry in tree:
        _render_entry(entry, 0, lines)
    return "\n".join(lines)


def _render_entry(entry: dict[str, Any], depth: int, lines: list[str]) -> None:
    indent = "  " * depth
    label = _render_label(entry)
    children = entry.get("children") or []
    if children:
        lines.append(f"{indent}{label}:")
        for child in children:
            _render_entry(child, depth + 1, lines)
    else:
        lines.append(f"{indent}{label}")


def _render_label(entry: dict[str, Any]) -> str:
    parts: list[str] = [str(entry.get("class", "Node"))]
    name = entry.get("name")
    if name:
        parts.append(f"#{name}")
    text = entry.get("text")
    if text:
        parts.append(f'"{_escape(str(text))}"')

    bracket: list[str] = []
    ref = entry.get("ref")
    if ref:
        bracket.append(f"ref={ref}")
    attrs = entry.get("attrs") or {}
    for k, v in attrs.items():
        bracket.append(f"{k}={_attr_value(v)}")
    flags = entry.get("flags") or []
    for f in flags:
        bracket.append(str(f))
    if bracket:
        parts.append("[" + ", ".join(bracket) + "]")

    return " ".join(parts)


def _attr_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return f'"{_escape(str(v))}"'


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')
