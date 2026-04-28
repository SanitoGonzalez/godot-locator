"""Shared fixtures for integration tests.

Each test gets a fresh Godot subprocess running a project from
`tests/projects/`, with the godot-locator plugin loaded. The fixture binds a
unique port per test so parallel runs (`pytest -n`) don't collide, then waits
for the plugin's WebSocket to accept connections before yielding a ready
`LocatorClient`.

Tests target a project via the `godot_project` marker — there's no default,
each test must opt in:

    @pytest.mark.godot_project("simple-ui")
    async def test_something(locator_client): ...
"""

from __future__ import annotations

import asyncio
import os
import socket
import subprocess
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio

from godot_locator_client import LocatorClient

PROJECTS_ROOT = Path(__file__).parent / "projects"
STARTUP_TIMEOUT_S = 10.0


def _free_port() -> int:
    """Ask the OS for an unused TCP port. Race-y in theory; fine in practice
    because the Godot side binds it within milliseconds of the probe close."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def _wait_for_port(host: str, port: int, timeout: float) -> None:
    deadline = asyncio.get_event_loop().time() + timeout
    last_err: Exception | None = None
    while asyncio.get_event_loop().time() < deadline:
        try:
            _, writer = await asyncio.open_connection(host, port)
            writer.close()
            await writer.wait_closed()
            return
        except (OSError, ConnectionRefusedError) as e:
            last_err = e
            await asyncio.sleep(0.1)
    raise TimeoutError(
        f"godot-locator on {host}:{port} did not accept connections within {timeout}s"
    ) from last_err


@pytest_asyncio.fixture
async def locator_client(request: pytest.FixtureRequest) -> AsyncIterator[LocatorClient]:
    """Per-test Godot + connected client. Tears down on test exit.

    The target project is read from the `godot_project` marker on the test
    function — there's no default."""
    marker = request.node.get_closest_marker("godot_project")
    if marker is None or not marker.args:
        raise pytest.UsageError(
            "test using `locator_client` must declare the target Godot project, "
            "e.g. `@pytest.mark.godot_project(\"simple-ui\")`"
        )
    project_name = marker.args[0]
    project_dir = PROJECTS_ROOT / project_name
    if not project_dir.is_dir():
        raise FileNotFoundError(f"unknown godot project: {project_dir}")
    port = _free_port()
    env = {**os.environ, "GODOT_LOCATOR_PORT": str(port)}
    proc = subprocess.Popen(
        ["godot", "--headless", "--path", str(project_dir)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        await _wait_for_port("127.0.0.1", port, STARTUP_TIMEOUT_S)
        client = LocatorClient(port=port)
        try:
            yield client
        finally:
            await client.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
