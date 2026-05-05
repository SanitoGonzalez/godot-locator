"""End-to-end smoke for the CLI.

Drives `godot-locator-cli` as a subprocess against a real Godot game via the
`cli` fixture. Verifies the installed entry point talks to the plugin all the
way down. Per-command behavior lives in dedicated tests.
"""

from __future__ import annotations

import pytest

from .conftest import CLIRunner


@pytest.mark.godot_project("simple-ui")
async def test_snapshot(cli: CLIRunner) -> None:
    result = cli("snapshot", "--json")
    payload = result.json()
    assert "snapshot" in payload
