"""Pytest harness: spawns one headless Godot per test, then exercises the MCP
tool layer via FastMCP's in-memory client.

The tool layer talks to Godot through a real WebSocket — we just bypass the
stdio MCP transport so we can call tools directly from Python. Test projects
live under the repo's top-level ``tests/projects/<name>/``.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from fastmcp import Client

from godot_locator_mcp import server as server_module
from godot_locator_mcp.client import LocatorClient

REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECTS = REPO_ROOT / "tests" / "projects"

GODOT_BIN = os.environ.get("GODOT_BIN", "godot")
BOOT_TIMEOUT_SECS = float(os.environ.get("GODOT_LOCATOR_BOOT_TIMEOUT", "15"))


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_port(port: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.05)
    return False


@dataclass
class GodotProc:
    project: str
    port: int
    proc: subprocess.Popen


def _start(project: str) -> GodotProc:
    project_dir = PROJECTS / project
    if not project_dir.is_dir():
        raise FileNotFoundError(f"no test project at {project_dir}")

    port = _free_port()
    env = os.environ.copy()
    env["GODOT_LOCATOR_PORT"] = str(port)
    env["GODOT_LOCATOR_HOST"] = "127.0.0.1"

    proc = subprocess.Popen(
        [GODOT_BIN, "--headless", "--path", str(project_dir)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    if not _wait_for_port(port, BOOT_TIMEOUT_SECS):
        proc.terminate()
        try:
            output, _ = proc.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            output = b""
        raise RuntimeError(
            f"godot did not open port {port} within {BOOT_TIMEOUT_SECS}s. "
            f"output:\n{output.decode(errors='replace')}"
        )

    return GodotProc(project=project, port=port, proc=proc)


def _stop(g: GodotProc) -> None:
    if g.proc.poll() is None:
        g.proc.terminate()
        try:
            g.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            g.proc.kill()


@pytest.fixture
def godot(request: pytest.FixtureRequest) -> Iterator[GodotProc]:
    if shutil.which(GODOT_BIN) is None:
        pytest.skip(f"'{GODOT_BIN}' not on PATH; integration test skipped")
    marker = request.node.get_closest_marker("project")
    project = marker.args[0] if marker else "simple"
    g = _start(project)
    try:
        yield g
    finally:
        _stop(g)


@pytest_asyncio.fixture
async def mcp_client(godot: GodotProc) -> AsyncIterator[Client]:
    """An in-memory MCP client wired to a fresh LocatorClient pointed at the
    test's Godot. We override the module-level client (instead of relying on
    env vars) so tests can run in parallel against different ports."""
    locator = LocatorClient(port=godot.port)
    server_module._set_client(locator)
    try:
        async with Client(server_module.mcp) as client:
            yield client
    finally:
        await locator.close()
        server_module._set_client(None)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "project(name): name of the Godot project under tests/projects/<name> to launch",
    )
