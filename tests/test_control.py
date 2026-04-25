"""TDD targets for control verbs (click, fill, ...).

Strategy: drive the fixture, then read state back via snapshot. The fixture's
Submit button updates a Status label on press, and the ClickPad ColorRect
mirrors double/right-click events into the same label, so each verb is
observable in the next snapshot.
"""

from client import Client
from snapshot import Node, expect_nodes


async def test_click_submit_updates_status(godot):
    async with Client(godot.port) as c:
        await c.call("click", locator={"name": "Submit"})
        yaml = await c.call("snapshot")
    expect_nodes(yaml, [Node("Label", name="Status", text="submitted: ")])


async def test_double_click_updates_status(godot):
    async with Client(godot.port) as c:
        await c.call("double_click", locator={"name": "ClickPad"})
        yaml = await c.call("snapshot")
    expect_nodes(yaml, [Node("Label", name="Status", text="double-clicked")])


async def test_right_click_updates_status(godot):
    async with Client(godot.port) as c:
        await c.call("right_click", locator={"name": "ClickPad"})
        yaml = await c.call("snapshot")
    expect_nodes(yaml, [Node("Label", name="Status", text="right-clicked")])


async def test_click_unknown_locator_errors(godot):
    async with Client(godot.port) as c:
        try:
            await c.call("click", locator={"name": "DoesNotExist"})
        except Exception as e:
            assert "no matches" in str(e).lower(), f"unexpected error: {e}"
        else:
            raise AssertionError("expected an error for an unmatched locator")


async def test_fill_updates_input_and_fires_text_changed(godot):
    """`fill` writes the text and emits `text_changed`; the CharCounter
    listens on that signal, so a counter update proves the signal fired."""
    async with Client(godot.port) as c:
        await c.call("fill", locator={"name": "NameInput"}, text="Sanito")
        yaml = await c.call("snapshot")
    expect_nodes(yaml, [
        Node("VBoxContainer", name="Form", children=[
            Node("LineEdit", name="NameInput", attrs={"text": "Sanito"}),
            Node("CharCounter", name="Counter", text="6/20"),
        ]),
    ])


async def test_fill_then_click_includes_typed_text(godot):
    async with Client(godot.port) as c:
        await c.call("fill", locator={"name": "NameInput"}, text="Sanito Gonzalez")
        await c.call("click", locator={"name": "Submit"})
        yaml = await c.call("snapshot")
    expect_nodes(yaml, [
        Node("VBoxContainer", name="Form", children=[
            Node("LineEdit", name="NameInput", attrs={"text": "Sanito Gonzalez"}),
            Node("CharCounter", name="Counter", text="15/20"),
            Node("Button", name="Submit", text="Submit"),
            Node("Label", name="Status", text="submitted: Sanito Gonzalez"),
        ]),
    ])
