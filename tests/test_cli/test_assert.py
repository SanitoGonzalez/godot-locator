"""`assert` / `wait` — selector-targeted condition polling.

These run headless: `exists`/`absent`/`count`/`disabled`/`value` and the
`visible` matcher (which reads `is_visible_in_tree`, independent of rendering)
all work without a real display.
"""

from __future__ import annotations

import pytest

from .conftest import CLIRunner


@pytest.mark.godot_project("simple-ui")
async def test_assert_exists_passes(cli: CLIRunner) -> None:
    out = cli("assert", "#SubmitButton", "exists").stdout
    assert out.startswith("PASS")


@pytest.mark.godot_project("simple-ui")
async def test_assert_absent_passes(cli: CLIRunner) -> None:
    cli("assert", "#NoSuchNode", "absent", "--timeout", "0.5").assert_ok()


@pytest.mark.godot_project("simple-ui")
async def test_assert_disabled_passes(cli: CLIRunner) -> None:
    # SubmitButton starts disabled (both inputs empty).
    cli("assert", "#SubmitButton", "disabled").assert_ok()


@pytest.mark.godot_project("simple-ui")
async def test_assert_visible_passes(cli: CLIRunner) -> None:
    cli("assert", "#Title", "visible").assert_ok()


@pytest.mark.godot_project("simple-ui")
async def test_assert_fail_exits_nonzero(cli: CLIRunner) -> None:
    result = cli("assert", "#NoSuchNode", "exists", "--timeout", "0.3", check=False)
    assert result.code == 1
    assert result.stdout.startswith("FAIL")


@pytest.mark.godot_project("simple-ui")
async def test_assert_value_after_selector_fill(cli: CLIRunner) -> None:
    # Both targeting forms are selectors here — exercises ref-free flow end to end.
    cli("fill", "#NameInput", "Bob").assert_ok()
    cli("assert", "#NameInput", "value", "Bob").assert_ok()


@pytest.mark.godot_project("simple-ui")
async def test_assert_text_matcher(cli: CLIRunner) -> None:
    cli("assert", "Label#Title", "text", "User Profile").assert_ok()


@pytest.mark.godot_project("simple-ui")
async def test_assert_count_matcher(cli: CLIRunner) -> None:
    cli("assert", "Button#CancelButton", "count", "1").assert_ok()
    # Nine numberpad cells.
    cli("assert", "Button#Cell1", "count", "1").assert_ok()


@pytest.mark.godot_project("simple-ui")
async def test_assert_property_matcher(cli: CLIRunner) -> None:
    cli("fill", "#NameInput", "Carol").assert_ok()
    cli("assert", "#NameInput", "property", "text", "Carol").assert_ok()


@pytest.mark.godot_project("simple-ui")
async def test_assert_json_output(cli: CLIRunner) -> None:
    result = cli("assert", "#SubmitButton", "exists", "--json").json()
    assert result["pass"] is True
    assert result["selector"] == "#SubmitButton"
    assert "snapshot" in result


@pytest.mark.godot_project("simple-ui")
async def test_wait_defaults_to_visible(cli: CLIRunner) -> None:
    cli("wait", "#Title").assert_ok()


@pytest.mark.godot_project("simple-ui")
async def test_interaction_ambiguous_selector_errors(cli: CLIRunner) -> None:
    result = cli("click", "Button", check=False)
    assert result.code != 0
    assert "matched" in result.stderr


@pytest.mark.godot_project("simple-ui")
@pytest.mark.godot_env(GODOT_LOCATOR_EVAL_ENABLED="true")
async def test_assert_expr_matcher(cli: CLIRunner) -> None:
    cli("fill", "#NameInput", "Dana").assert_ok()
    cli("assert", "#NameInput", "expr", "node.text == 'Dana'").assert_ok()
