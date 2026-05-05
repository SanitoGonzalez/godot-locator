"""`resize` — resize the running game's window."""

from __future__ import annotations

import pytest

from .conftest import CLIRunner


@pytest.mark.godot_project("simple-ui")
async def test_resize_returns_post_snapshot(cli: CLIRunner) -> None:
    cli("snapshot", "--json").assert_ok()
    payload = cli("resize", "640", "480", "--json").json()
    assert payload["mode"] == "full"
    assert "tree" in payload["snapshot"]


@pytest.mark.godot_project("simple-ui")
async def test_resize_zero_dimensions_errors(cli: CLIRunner) -> None:
    cli("snapshot", "--json").assert_ok()
    result = cli("resize", "0", "0", check=False)
    assert result.code != 0
