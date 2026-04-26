"""TDD targets for the YAML SceneTree snapshot.

These tests will fail until `_snapshot` in `addons/godot-locator/service.gd`
is implemented for real (currently returns a placeholder). That's the point.
"""

from client import Client
from snapshot import Node, expect_nodes, parse


async def test_snapshot_is_a_string(godot):
    async with Client(godot.port) as c:
        yaml = await c.call("snapshot")
    assert isinstance(yaml, str), f"expected YAML string, got {yaml!r}"


async def test_snapshot_matches_form_structure(godot):
    async with Client(godot.port) as c:
        yaml = await c.call("snapshot")
    expect_nodes(
        yaml,
        [
            Node("VBoxContainer", name="Form", children=[
                Node("Label", name="Title", text="Welcome"),
                Node("LineEdit", name="NameInput", attrs={"placeholder": "Name"}),
                Node("CharCounter", name="Counter"),
                Node("Button", name="Submit", text="Submit"),
                Node("Label", name="Status"),
            ]),
        ],
    )


async def test_custom_node_uses_format_hook(godot):
    """CharCounter implements `_godot_locator_format` → its line carries the
    hook's text/attrs, and with `tag_ref=true` the plugin auto-issues a ref."""
    async with Client(godot.port) as c:
        yaml = await c.call("snapshot", tag_ref=True)
    expect_nodes(
        yaml,
        [Node("CharCounter", name="Counter", text="0/20", attrs={"max": "20"})],
    )
    counter = next(n for n in parse(yaml) if n.cls == "CharCounter")
    assert counter.ref is not None and counter.ref.startswith("e"), (
        f"expected auto-issued ref for custom node, got {counter.ref!r}"
    )
    assert "full" not in counter.flags, "counter should not be 'full' at 0/20"


async def test_snapshot_omits_refs_by_default(godot):
    """Refs are opt-in (Playwright-style). A plain `snapshot` call must not
    emit `ref=eN` markers, even for interactive nodes."""
    async with Client(godot.port) as c:
        yaml = await c.call("snapshot")
    assert "ref=" not in yaml, f"expected no refs in default snapshot, got:\n{yaml}"
    assert all(n.ref is None for n in parse(yaml))


async def test_csharp_custom_node_unicode_roundtrip(godot):
    """C# custom node (`KoreanButton : Button`):
      - `_GodotLocatorFormat` is picked up via the PascalCase fallback.
      - Korean text round-trips through WS/JSON/snapshot without mojibake.
      - Button.Text set in C# `_Ready` reaches the default formatter.
    """
    async with Client(godot.port) as c:
        yaml = await c.call("snapshot")
    expect_nodes(
        yaml,
        [
            Node(
                "KoreanButton",
                name="Korean",
                text="제출",
                attrs={"greeting": "안녕하세요"},
            )
        ],
    )
