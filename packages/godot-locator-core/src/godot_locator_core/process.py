"""Cross-platform Godot process spawn / liveness / terminate.

The spawned Godot must outlive the CLI invocation, so we detach with
platform-appropriate flags (POSIX session vs. Windows DETACHED_PROCESS).
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

DEFAULT_GODOT_BIN = "godot"
ENV_GODOT_BIN = "GODOT_BIN"
ENV_LOCATOR_PORT = "GODOT_LOCATOR_PORT"
ENV_LOCATOR_HOST = "GODOT_LOCATOR_HOST"


def find_free_port() -> int:
    """Ask the OS for an ephemeral port. Race-y in theory; the Godot side
    binds within milliseconds of the probe close, so it's fine in practice."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def godot_bin() -> str:
    """Resolve the Godot binary. Honors `GODOT_BIN` for users who keep
    multiple versions side by side (common on macOS via .app bundles)."""
    return os.environ.get(ENV_GODOT_BIN, DEFAULT_GODOT_BIN)


@dataclass
class GodotProcess:
    pid: int
    endpoint: str
    port: int


def launch(
    project_path: Path,
    *,
    headless: bool = False,
    resolution: tuple[int, int] | None = None,
    port: int | None = None,
    host: str = "127.0.0.1",
    extra_args: list[str] | None = None,
) -> GodotProcess:
    """Start a detached Godot process and return its handle.

    Caller is responsible for waiting until the WebSocket is reachable
    (see `wait_for_endpoint`) and for persisting the returned `pid` into
    the session file so `terminate` can find it later.
    """
    if not project_path.is_dir():
        raise FileNotFoundError(f"project path not found: {project_path}")
    bound_port = port if port is not None else find_free_port()

    args = [godot_bin(), "--path", str(project_path)]
    if headless:
        args.append("--headless")
    if resolution is not None:
        width, height = resolution
        args.extend(["--resolution", f"{width}x{height}"])
    if extra_args:
        args.extend(extra_args)

    env = {
        **os.environ,
        ENV_LOCATOR_PORT: str(bound_port),
        ENV_LOCATOR_HOST: host,
    }

    if sys.platform == "win32":
        # DETACHED_PROCESS so the child survives the CLI's exit; new process
        # group so Ctrl-C in the CLI's console doesn't propagate to the game.
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        proc = subprocess.Popen(
            args,
            env=env,
            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        # `start_new_session=True` puts the child in its own session/process
        # group — same effect as `setsid`, parent can exit without SIGHUP.
        proc = subprocess.Popen(
            args,
            env=env,
            start_new_session=True,
            close_fds=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    return GodotProcess(pid=proc.pid, endpoint=f"ws://{host}:{bound_port}", port=bound_port)


def wait_for_endpoint(host: str, port: int, timeout_s: float = 10.0) -> None:
    """Block until a TCP connect to `host:port` succeeds or `timeout_s` passes."""
    deadline = time.monotonic() + timeout_s
    last_err: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError as e:
            last_err = e
            time.sleep(0.1)
    raise TimeoutError(
        f"godot-locator on {host}:{port} did not accept connections within {timeout_s}s"
    ) from last_err


def is_alive(pid: int) -> bool:
    """Best-effort PID liveness check — works on all three target OSes."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we can't signal it — still alive from our POV.
        return True
    except OSError:
        return False
    return True


def terminate(pid: int) -> bool:
    """Send SIGTERM (POSIX) or `TerminateProcess` (Windows). Returns True if
    the process was alive and we issued the signal."""
    if not is_alive(pid):
        return False
    try:
        if sys.platform == "win32":
            import signal
            os.kill(pid, signal.SIGTERM)
        else:
            import signal
            os.kill(pid, signal.SIGTERM)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False
