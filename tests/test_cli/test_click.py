"""`click` — synthesize a mouse click on a node."""

from __future__ import annotations

import pytest

from .conftest import CLIRunner, find_node


@pytest.mark.godot_project("simple-ui")
async def test_click_cancel_clears_form(cli: CLIRunner) -> None:
    snap = cli("snapshot", "--json").json()["snapshot"]
    name_ref = find_node(snap, name="NameInput")["ref"]
    email_ref = find_node(snap, name="EmailInput")["ref"]
    cancel_ref = find_node(snap, name="CancelButton")["ref"]

    cli("fill", name_ref, "Alice").assert_ok()
    cli("fill", email_ref, "alice@example.com").assert_ok()
    after = cli("click", cancel_ref, "--json").json()["snapshot"]

    assert find_node(after, name="NameInput").get("text", "") == ""
    assert find_node(after, name="EmailInput").get("text", "") == ""
    assert "disabled" in find_node(after, name="SubmitButton").get("flags", [])


@pytest.mark.godot_project("simple-ui")
async def test_click_text_output_includes_snapshot(cli: CLIRunner) -> None:
    snap = cli("snapshot", "--json").json()["snapshot"]
    cancel_ref = find_node(snap, name="CancelButton")["ref"]

    out = cli("click", cancel_ref).stdout
    assert "### Snapshot" in out


@pytest.mark.godot_project("simple-ui")
async def test_click_no_snapshot_flag_suppresses_block(cli: CLIRunner) -> None:
    snap = cli("snapshot", "--json").json()["snapshot"]
    cancel_ref = find_node(snap, name="CancelButton")["ref"]

    out = cli("click", cancel_ref, "--no-snapshot").stdout
    assert "### Snapshot" not in out


@pytest.mark.godot_project("simple-ui")
@pytest.mark.godot_display
async def test_click_submit_records_attrs(cli: CLIRunner) -> None:
    # SubmitButton's center is far from the origin, so headless's 64x64 dummy
    # viewport drops the click event. Needs a real layout to land.
    snap = cli("snapshot", "--json").json()["snapshot"]
    name_ref = find_node(snap, name="NameInput")["ref"]
    email_ref = find_node(snap, name="EmailInput")["ref"]
    submit_ref = find_node(snap, name="SubmitButton")["ref"]

    cli("fill", name_ref, "Alice").assert_ok()
    cli("fill", email_ref, "alice@example.com").assert_ok()
    after = cli("click", submit_ref, "--json").json()["snapshot"]

    # main.gd's `_on_submit` clears both inputs and stores the values on
    # `Root`, which surfaces them via `_godot_locator_format().attrs`.
    assert find_node(after, name="NameInput").get("text", "") == ""
    assert find_node(after, name="EmailInput").get("text", "") == ""
    root_attrs = find_node(after, name="Root").get("attrs", {})
    assert root_attrs.get("submitted_name") == "Alice"
    assert root_attrs.get("submitted_email") == "alice@example.com"


@pytest.mark.godot_project("simple-ui")
async def test_click_invalid_button_errors(cli: CLIRunner) -> None:
    snap = cli("snapshot", "--json").json()["snapshot"]
    cancel_ref = find_node(snap, name="CancelButton")["ref"]

    result = cli("click", cancel_ref, "purple", check=False)
    assert result.code != 0
