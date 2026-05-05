"""`type` and `press` — synthesize keyboard input."""

from __future__ import annotations

import pytest

from .conftest import CLIRunner, find_node


@pytest.mark.godot_project("simple-ui")
async def test_type_into_focused_input(cli: CLIRunner) -> None:
    snap = cli("snapshot", "--json").json()["snapshot"]
    name_ref = find_node(snap, name="NameInput")["ref"]

    # Click focuses the LineEdit so `type` has a target.
    cli("click", name_ref).assert_ok()
    after = cli("type", "Hello", "--json").json()["snapshot"]

    assert find_node(after, name="NameInput").get("text") == "Hello"


@pytest.mark.godot_project("simple-ui")
async def test_type_without_focus_errors(cli: CLIRunner) -> None:
    cli("snapshot", "--json").assert_ok()
    result = cli("type", "Hello", check=False)
    assert result.code != 0
    assert "focus" in result.stderr.lower()


@pytest.mark.godot_project("simple-ui")
async def test_press_unknown_key_errors(cli: CLIRunner) -> None:
    cli("snapshot", "--json").assert_ok()
    result = cli("press", "totally-not-a-key", check=False)
    assert result.code != 0


@pytest.mark.godot_project("simple-ui")
async def test_press_known_key(cli: CLIRunner) -> None:
    snap = cli("snapshot", "--json").json()["snapshot"]
    name_ref = find_node(snap, name="NameInput")["ref"]
    cli("click", name_ref).assert_ok()
    cli("type", "abc").assert_ok()
    # Backspace deletes the last character.
    after = cli("press", "backspace", "--json").json()["snapshot"]
    assert find_node(after, name="NameInput").get("text") == "ab"
