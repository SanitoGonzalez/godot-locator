"""Snapshot text parser + assertion helper for integration tests.

The runtime service emits a YAML-flavored line per node. This module parses that
text into ``Node`` records and provides ``expect_nodes`` for ordered, structural
assertions in tests — instead of ``assert "Submit" in yaml``.

Snapshot line shape::

    [<indent>]- <Class>[ [<name>[ ref=<ref>]]][ "<text>"][ <key>="<value>"]*[ <flag>]*[:]

Indent is two spaces per depth. Trailing ``:`` indicates the node has children.
``ref`` is issued for interactive nodes (LineEdit/TextEdit/BaseButton) and any
node implementing ``_godot_locator_format``.

Hierarchy: ``expect_nodes`` matches the expected list as a contiguous run of
*siblings* at some level of the parsed tree. To assert parent/child structure,
nest expectations via ``Node(..., children=[Node(...), ...])``. Flat-listing a
parent followed by one of its descendants no longer matches.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from typing import Optional


@dataclass(frozen=True)
class Node:
    """A constraint OR a parsed entry, depending on context.

    As an *expectation*, only fields explicitly set are checked — ``cls`` is
    always required, the rest are matched only if non-default. Setting
    ``children=[...]`` asserts hierarchy: each expected child must appear as a
    contiguous subsequence among the matched node's actual children.

    As a *parsed* entry, ``parse`` returns flat nodes (``children=()``).
    ``expect_nodes`` builds the tree internally for matching.
    """

    cls: str
    name: Optional[str] = None
    ref: Optional[str] = None
    text: Optional[str] = None
    attrs: dict[str, str] = field(default_factory=dict)
    flags: frozenset[str] = field(default_factory=frozenset)
    depth: Optional[int] = None
    children: tuple["Node", ...] = ()

    def __post_init__(self) -> None:
        # accept any iterable for ergonomics; store as tuple for stable equality
        if not isinstance(self.children, tuple):
            object.__setattr__(self, "children", tuple(self.children))

    def render(self) -> str:
        parts = [self.cls]
        if self.name is not None or self.ref is not None:
            inner = []
            if self.name is not None:
                inner.append(self.name)
            if self.ref is not None:
                inner.append(f"ref={self.ref}")
            parts.append(f"[{' '.join(inner)}]")
        if self.text is not None:
            parts.append(f'"{self.text}"')
        for k in sorted(self.attrs):
            parts.append(f'{k}="{self.attrs[k]}"')
        for f in sorted(self.flags):
            parts.append(f)
        return " ".join(parts)


# --- parser -------------------------------------------------------------------

_LINE = re.compile(
    r"^(?P<indent>(?:  )*)- "
    r"(?P<cls>[A-Za-z]\w*)"
    r"(?P<rest>.*?)"
    r"(?P<has_children>:)?$"
)
_NAME = re.compile(r" \[(?P<name>[^\]]+?)(?: ref=(?P<ref>e\d+))?\]")
_TEXT = re.compile(r' "(?P<text>(?:[^"\\]|\\.)*)"')
_KV = re.compile(r' (?P<key>\w+)="(?P<val>(?:[^"\\]|\\.)*)"')
_FLAG = re.compile(r" (?P<flag>\w+)(?=\s|$)")


def parse(snapshot: str) -> list[Node]:
    """Return the parsed node list in DFS preorder. Each node carries its
    ``depth`` but ``children`` is always ``()`` — use ``expect_nodes`` (or
    ``_build_tree``) if you need the hierarchy populated. Raises on malformed
    lines."""
    if not isinstance(snapshot, str):
        raise TypeError(
            f"snapshot must be a string, got {type(snapshot).__name__}: {snapshot!r}"
        )
    nodes: list[Node] = []
    for raw in snapshot.splitlines():
        line = raw.rstrip()
        if not line or not line.lstrip().startswith("-"):
            continue
        m = _LINE.match(line)
        if not m:
            raise ValueError(f"unparseable snapshot line: {line!r}")
        depth = len(m.group("indent")) // 2
        cls = m.group("cls")
        rest = m.group("rest")

        name_m = _NAME.search(rest)
        name = name_m.group("name") if name_m else None
        ref = name_m.group("ref") if name_m else None
        if name_m:
            rest = rest[: name_m.start()] + rest[name_m.end():]

        text_m = _TEXT.search(rest)
        text = text_m.group("text") if text_m else None
        if text_m:
            rest = rest[: text_m.start()] + rest[text_m.end():]

        attrs: dict[str, str] = {}
        # iterate without overlap by repeatedly stripping matches
        while True:
            kv = _KV.search(rest)
            if not kv:
                break
            attrs[kv.group("key")] = kv.group("val")
            rest = rest[: kv.start()] + rest[kv.end():]

        flags = {fm.group("flag") for fm in _FLAG.finditer(rest)}

        nodes.append(
            Node(cls=cls, name=name, ref=ref, text=text, attrs=attrs, flags=frozenset(flags), depth=depth)
        )
    return nodes


def _build_tree(flat: list[Node]) -> list[Node]:
    """Convert a flat DFS list (as from ``parse``) into a forest with
    ``children`` populated from the indent levels."""
    if not flat:
        return []

    children_idx: list[list[int]] = [[] for _ in flat]
    roots: list[int] = []
    open_stack: list[int] = []  # indexes of currently-open ancestors

    for i, n in enumerate(flat):
        d = n.depth or 0
        while len(open_stack) > d:
            open_stack.pop()
        if d > 0 and len(open_stack) == d:
            children_idx[open_stack[-1]].append(i)
        else:
            # depth 0 or malformed depth jump — treat as a new root
            roots.append(i)
        open_stack.append(i)

    def freeze(idx: int) -> Node:
        return replace(flat[idx], children=tuple(freeze(c) for c in children_idx[idx]))

    return [freeze(i) for i in roots]


# --- assertion ----------------------------------------------------------------

def _matches_self(want: Node, got: Node) -> bool:
    """Field-level match, ignoring children."""
    if want.cls != got.cls:
        return False
    if want.name is not None and want.name != got.name:
        return False
    if want.ref is not None and want.ref != got.ref:
        return False
    if want.text is not None and want.text != got.text:
        return False
    for k, v in want.attrs.items():
        if got.attrs.get(k) != v:
            return False
    if want.flags and not want.flags.issubset(got.flags):
        return False
    if want.depth is not None and want.depth != got.depth:
        return False
    return True


def _matches_node(want: Node, got: Node) -> bool:
    """Match ``want`` (with optional ``children``) against an actual node."""
    if not _matches_self(want, got):
        return False
    if not want.children:
        return True
    return _find_subsequence(list(got.children), list(want.children))


def _find_subsequence(actual: list[Node], expected: list[Node]) -> bool:
    """Find ``expected`` as a contiguous subsequence in ``actual``."""
    if not expected:
        return True
    if len(expected) > len(actual):
        return False
    for start in range(len(actual) - len(expected) + 1):
        if all(_matches_node(w, actual[start + i]) for i, w in enumerate(expected)):
            return True
    return False


def _find_anywhere(siblings: list[Node], expected: list[Node]) -> bool:
    """Try ``expected`` as a contiguous sibling subsequence at this level,
    then recurse into each node's children."""
    if _find_subsequence(siblings, expected):
        return True
    for n in siblings:
        if _find_anywhere(list(n.children), expected):
            return True
    return False


def _render_expected(out: list[str], n: Node, depth: int) -> None:
    pad = "  " * depth
    out.append(f"{pad}- {n.render()}")
    for c in n.children:
        _render_expected(out, c, depth + 1)


def _format_mismatch(snapshot: str, expected: Iterable[Node]) -> str:
    out = ["snapshot did not match expected sequence", "", "expected:"]
    for w in expected:
        _render_expected(out, w, depth=0)
    out.append("")
    out.append("actual:")
    out.append("")
    out.append("full snapshot:")
    out.append(snapshot.rstrip())
    return "\n".join(out)


def expect_nodes(snapshot: str, expected: list[Node], *, strict: bool = False) -> None:
    """Assert ``expected`` appears as a sibling run in the parsed tree.

    Default mode finds ``expected`` as a contiguous run of siblings at *some*
    level of the actual tree (root, or any node's children). To enforce that a
    node's actual descendants contain certain children, set ``children=[...]``
    on the expectation; those children must in turn appear as a contiguous
    subsequence of the matched node's actual children.

    ``strict=True`` requires ``expected`` to match the root level exactly —
    same length, same order. Children matching cascades the same
    contiguous-subsequence rule.

    Each ``Node`` field is checked only when set on the expectation. Class is
    always required; name/ref/text/attrs/flags/depth are optional. Listing a
    parent and one of its descendants as flat siblings is now an error — use
    ``children=[...]``.
    """
    flat = parse(snapshot)
    if not flat:
        raise AssertionError(f"snapshot parsed to zero nodes:\n{snapshot}")
    forest = _build_tree(flat)

    if strict:
        if (
            len(forest) != len(expected)
            or not all(_matches_node(w, g) for w, g in zip(expected, forest))
        ):
            raise AssertionError(_format_mismatch(snapshot, expected))
        return

    if _find_anywhere(forest, expected):
        return
    raise AssertionError(_format_mismatch(snapshot, expected))
