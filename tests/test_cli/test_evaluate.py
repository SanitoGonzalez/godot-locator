"""`eval` — evaluate a single GDScript expression in the running game.

Requires `GODOT_LOCATOR_EVAL_ENABLED=true` on the Godot process; tests opt in
via the `godot_env` marker.
"""

from __future__ import annotations

import pytest

from .conftest import CLIRunner, find_node


@pytest.mark.godot_project("simple-ui")
@pytest.mark.godot_env(GODOT_LOCATOR_EVAL_ENABLED="true")
async def test_eval_arithmetic(cli: CLIRunner) -> None:
    out = cli("eval", "1 + 2 + 3").stdout.strip()
    assert out == "6"


@pytest.mark.godot_project("simple-ui")
@pytest.mark.godot_env(GODOT_LOCATOR_EVAL_ENABLED="true")
async def test_eval_with_node_ref(cli: CLIRunner) -> None:
    snap = cli("snapshot", "--json").json()["snapshot"]
    submit_ref = find_node(snap, name="SubmitButton")["ref"]

    payload = cli("eval", "node.text", "--ref", submit_ref, "--json").json()
    assert payload == {"value": "Submit"}


@pytest.mark.godot_project("simple-ui")
async def test_eval_disabled_by_default(cli: CLIRunner) -> None:
    result = cli("eval", "1 + 1", check=False)
    assert result.code != 0
    assert "GODOT_LOCATOR_EVAL_ENABLED" in result.stderr


@pytest.mark.godot_project("simple-ui")
@pytest.mark.godot_env(GODOT_LOCATOR_EVAL_ENABLED="true")
async def test_eval_parse_error(cli: CLIRunner) -> None:
    result = cli("eval", "1 + ", check=False)
    assert result.code != 0
    assert "parse" in result.stderr.lower()
