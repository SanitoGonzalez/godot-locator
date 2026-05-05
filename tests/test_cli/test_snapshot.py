"""`snapshot` rendering and content."""

from __future__ import annotations

import pytest

from .conftest import CLIRunner, find_node


@pytest.mark.godot_project("simple-ui")
async def test_snapshot_json_payload(cli: CLIRunner) -> None:
    snap = cli("snapshot", "--json").json()["snapshot"]
    assert isinstance(snap.get("tree"), list)
    assert snap["context"]["description"] == "This is a custom context description"

    submit = find_node(snap, name="SubmitButton")
    assert submit["class"] == "Button"
    assert "disabled" in submit.get("flags", [])

    name_input = find_node(snap, name="NameInput")
    assert name_input["class"] == "LineEdit"
    assert name_input["attrs"]["placeholder"] == "Full name"
    assert name_input["ref"].startswith("e")


@pytest.mark.godot_project("simple-ui")
async def test_snapshot_picks_up_custom_format(cli: CLIRunner) -> None:
    snap = cli("snapshot", "--json").json()["snapshot"]
    root = snap["tree"][0]
    assert root["text"] == "this is a custom text"
    assert root["attrs"]["submitted_name"] == ""
    assert root["attrs"]["submitted_email"] == ""
    assert "this is a custom tag" in root["flags"]


@pytest.mark.godot_project("simple-ui")
async def test_snapshot_text_output(cli: CLIRunner) -> None:
    out = cli("snapshot").stdout
    assert "### Snapshot" in out
    assert "### Context" in out
    assert "User Profile" in out
    assert "SubmitButton" in out


@pytest.mark.godot_project("simple-ui")
async def test_snapshot_depth_limits_children(cli: CLIRunner) -> None:
    snap = cli("snapshot", "--depth", "1", "--json").json()["snapshot"]
    for top in snap["tree"]:
        assert top["children"] == [], top
