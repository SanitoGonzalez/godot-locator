"""End-to-end smoke for the CLI.

Invokes the installed `godot-locator-cli` entry point as a subprocess against
a real Godot game and asserts a clean exit. The CLI is currently a stub, so
this test mostly verifies the entry point is wired and the fixture stack
holds together; it'll grow real assertions as the CLI grows commands.
"""

from __future__ import annotations

import os
import subprocess

import pytest

from godot_locator_client import LocatorClient


@pytest.mark.godot_project("simple-ui")
async def test_cli_runs(locator_client: LocatorClient) -> None:
    result = subprocess.run(
        ["godot-locator-cli"],
        env={**os.environ, "GODOT_LOCATOR_PORT": str(locator_client.port)},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
