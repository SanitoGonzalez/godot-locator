"""CLI integration-test fixtures.

The `cli` fixture wraps the subprocess + session-attach boilerplate. It
depends on `locator_client` to spawn Godot, isolates `GODOT_LOCATOR_DATA_HOME`
to a `tmp_path`, and pre-attaches a `default` session at the running game's
port. Tests just call `cli("snapshot", "--json")` and inspect the result.
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import pytest_asyncio

from godot_locator_core import LocatorClient, Session, SessionStore


def find_node(snapshot: dict, *, name: str) -> dict:
    """Walk `snapshot["tree"]` and return the first entry with `name`.

    Tests use this so they don't hardcode ref ids — refs depend on traversal
    order and are easy to break by editing the scene."""
    def _walk(entry: dict) -> dict | None:
        if entry.get("name") == name:
            return entry
        for child in entry.get("children") or []:
            found = _walk(child)
            if found is not None:
                return found
        return None

    for top in snapshot.get("tree", []):
        found = _walk(top)
        if found is not None:
            return found
    raise AssertionError(f"node {name!r} not found in snapshot")


@dataclass
class CLIResult:
    args: tuple[str, ...]
    code: int
    stdout: str
    stderr: str

    def assert_ok(self) -> CLIResult:
        if self.code != 0:
            raise AssertionError(self._format("exited %d" % self.code))
        return self

    def json(self) -> Any:
        try:
            return json.loads(self.stdout)
        except json.JSONDecodeError as e:
            raise AssertionError(self._format(f"stdout is not JSON ({e})")) from e

    def _format(self, headline: str) -> str:
        return (
            f"`godot-locator-cli {' '.join(self.args)}` {headline}\n"
            f"--- stdout ---\n{self.stdout}"
            f"--- stderr ---\n{self.stderr}"
        )


class CLIRunner(Protocol):
    def __call__(
        self,
        *args: str,
        check: bool = ...,
        timeout: float = ...,
        input: str | None = ...,
    ) -> CLIResult: ...


@pytest_asyncio.fixture
async def cli(
    locator_client: LocatorClient,
    tmp_path: Path,
) -> AsyncIterator[CLIRunner]:
    """Yield a callable that runs `godot-locator-cli` against the fixture's
    Godot game. Asserts a clean exit by default; pass `check=False` to test
    failure paths."""
    data_home = tmp_path / "godot-locator-data"
    SessionStore(root=data_home / "sessions").save(
        Session(name="default", endpoint=f"ws://127.0.0.1:{locator_client.port}")
    )
    env = {**os.environ, "GODOT_LOCATOR_DATA_HOME": str(data_home)}

    def run(
        *args: str,
        check: bool = True,
        timeout: float = 10.0,
        input: str | None = None,
    ) -> CLIResult:
        proc = subprocess.run(
            ["godot-locator-cli", *args],
            env=env,
            input=input,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        result = CLIResult(
            args=tuple(args),
            code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
        if check:
            result.assert_ok()
        return result

    yield run
