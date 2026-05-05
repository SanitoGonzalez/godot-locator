"""`attach`, `detach`, and `sessions list/rm`. These don't need a running
Godot — they exercise just the on-disk session store and reachability
probes."""

from __future__ import annotations

import json
import os
import socket
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest


@dataclass
class CLIResult:
    code: int
    stdout: str
    stderr: str


@pytest.fixture
def cli_no_godot(tmp_path: Path) -> Iterator:
    """Run `godot-locator-cli` with an isolated `GODOT_LOCATOR_DATA_HOME`."""
    env = {**os.environ, "GODOT_LOCATOR_DATA_HOME": str(tmp_path / "data")}

    def run(*args: str, check: bool = True, timeout: float = 5.0) -> CLIResult:
        proc = subprocess.run(
            ["godot-locator-cli", *args],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        result = CLIResult(code=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
        if check and proc.returncode != 0:
            raise AssertionError(
                f"`godot-locator-cli {' '.join(args)}` exited {proc.returncode}\n"
                f"--- stdout ---\n{proc.stdout}--- stderr ---\n{proc.stderr}"
            )
        return result

    yield run


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_sessions_list_empty(cli_no_godot) -> None:
    result = cli_no_godot("sessions", "list")
    assert "(no sessions)" in result.stdout


def test_attach_no_probe_saves_session(cli_no_godot) -> None:
    endpoint = "ws://127.0.0.1:65500"
    cli_no_godot("attach", "--endpoint", endpoint, "--no-probe")

    rows = json.loads(cli_no_godot("sessions", "list", "--json").stdout)
    assert len(rows) == 1
    assert rows[0]["name"] == "default"
    assert rows[0]["endpoint"] == endpoint


def test_attach_probe_rejects_dead_endpoint(cli_no_godot) -> None:
    # A free port has nothing listening — the probe must report it and skip
    # writing the session file.
    dead_port = _free_port()
    result = cli_no_godot(
        "attach", "--endpoint", f"ws://127.0.0.1:{dead_port}", check=False
    )
    assert "not reachable" in result.stderr
    assert "(no sessions)" in cli_no_godot("sessions", "list").stdout


def test_detach_removes_session(cli_no_godot) -> None:
    cli_no_godot("attach", "--endpoint", "ws://127.0.0.1:65500", "--no-probe")
    cli_no_godot("detach")
    assert "(no sessions)" in cli_no_godot("sessions", "list").stdout


def test_detach_without_session_errors(cli_no_godot) -> None:
    result = cli_no_godot("detach", check=False)
    assert "not found" in result.stderr or "no session" in result.stderr.lower()


def test_sessions_rm(cli_no_godot) -> None:
    cli_no_godot("-s", "alpha", "attach", "--endpoint", "ws://127.0.0.1:65500", "--no-probe")
    cli_no_godot("-s", "beta", "attach", "--endpoint", "ws://127.0.0.1:65501", "--no-probe")

    cli_no_godot("sessions", "rm", "alpha")

    rows = json.loads(cli_no_godot("sessions", "list", "--json").stdout)
    names = {r["name"] for r in rows}
    assert names == {"beta"}


def test_sessions_rm_missing_errors(cli_no_godot) -> None:
    result = cli_no_godot("sessions", "rm", "ghost", check=False)
    assert "ghost" in result.stderr
