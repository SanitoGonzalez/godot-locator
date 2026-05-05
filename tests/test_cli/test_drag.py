"""`drag` — synthesize a press-move-release gesture between two node refs.

Exercises the NumberPad in `simple-ui`: dragging from cell N to cell M paints
every cell whose rect overlaps the bounding box. The pad's
`_godot_locator_format` exposes the selection as
`text = "selected: 1, 2, 4, 5"`, which is what the test asserts on.

Needs a real display — under headless's 64x64 viewport the pad's children
aren't laid out at their declared positions, so the drag rect math doesn't
land on the expected cells."""

from __future__ import annotations

import pytest

from .conftest import CLIRunner, find_node


@pytest.mark.godot_project("simple-ui")
@pytest.mark.godot_display
async def test_drag_paints_bounding_rect(cli: CLIRunner) -> None:
    snap = cli("snapshot", "--json").json()["snapshot"]
    assert find_node(snap, name="NumberPad")["text"].startswith("drag and drop")
    cell1_ref = find_node(snap, name="Cell1")["ref"]
    cell5_ref = find_node(snap, name="Cell5")["ref"]

    after = cli("drag", cell1_ref, cell5_ref, "--json").json()["snapshot"]

    # Cells 1, 2, 4, 5 form the bounding rect from cell 1's center to cell 5's.
    assert find_node(after, name="NumberPad")["text"] == "selected: 1, 2, 4, 5"


@pytest.mark.godot_project("simple-ui")
@pytest.mark.godot_display
async def test_drag_on_selected_cell_deselects(cli: CLIRunner) -> None:
    snap = cli("snapshot", "--json").json()["snapshot"]
    cell1_ref = find_node(snap, name="Cell1")["ref"]
    cell9_ref = find_node(snap, name="Cell9")["ref"]
    cell5_ref = find_node(snap, name="Cell5")["ref"]

    # First drag selects every cell.
    after = cli("drag", cell1_ref, cell9_ref, "--json").json()["snapshot"]
    assert find_node(after, name="NumberPad")["text"] == "selected: 1, 2, 3, 4, 5, 6, 7, 8, 9"

    # Second drag starts on a selected cell — the pad flips into "erase"
    # mode and clears the cells in the bounding rect (1, 2, 4, 5).
    after = cli("drag", cell1_ref, cell5_ref, "--json").json()["snapshot"]
    assert find_node(after, name="NumberPad")["text"] == "selected: 3, 6, 7, 8, 9"
