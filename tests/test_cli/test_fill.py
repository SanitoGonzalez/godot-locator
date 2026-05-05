"""`fill` — replace a LineEdit/TextEdit's text atomically."""

from __future__ import annotations

import pytest

from .conftest import CLIRunner, find_node


@pytest.mark.godot_project("simple-ui")
async def test_fill_sets_input_text(cli: CLIRunner) -> None:
    snap = cli("snapshot", "--json").json()["snapshot"]
    name_ref = find_node(snap, name="NameInput")["ref"]

    payload = cli("fill", name_ref, "Alice", "--json").json()
    assert find_node(payload["snapshot"], name="NameInput").get("text") == "Alice"


@pytest.mark.godot_project("simple-ui")
async def test_fill_both_inputs_enables_submit(cli: CLIRunner) -> None:
    snap = cli("snapshot", "--json").json()["snapshot"]
    name_ref = find_node(snap, name="NameInput")["ref"]
    email_ref = find_node(snap, name="EmailInput")["ref"]

    cli("fill", name_ref, "Alice").assert_ok()
    after = cli("fill", email_ref, "alice@example.com", "--json").json()["snapshot"]

    submit = find_node(after, name="SubmitButton")
    assert "disabled" not in submit.get("flags", [])


@pytest.mark.godot_project("simple-ui")
async def test_fill_one_input_keeps_submit_disabled(cli: CLIRunner) -> None:
    snap = cli("snapshot", "--json").json()["snapshot"]
    name_ref = find_node(snap, name="NameInput")["ref"]

    after = cli("fill", name_ref, "Alice", "--json").json()["snapshot"]
    submit = find_node(after, name="SubmitButton")
    assert "disabled" in submit.get("flags", [])


@pytest.mark.godot_project("simple-ui")
async def test_fill_on_button_errors(cli: CLIRunner) -> None:
    snap = cli("snapshot", "--json").json()["snapshot"]
    cancel_ref = find_node(snap, name="CancelButton")["ref"]

    result = cli("fill", cancel_ref, "X", check=False)
    assert result.code != 0
    assert "LineEdit" in result.stderr or "TextEdit" in result.stderr


@pytest.mark.godot_project("simple-ui")
async def test_fill_unknown_ref_errors(cli: CLIRunner) -> None:
    cli("snapshot", "--json").assert_ok()
    result = cli("fill", "e9999", "x", check=False)
    assert result.code != 0
    assert "unknown ref" in result.stderr.lower()
