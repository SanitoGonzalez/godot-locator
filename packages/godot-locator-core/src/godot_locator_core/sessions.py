"""Session model, on-disk store, and resolution rules.

On-disk format:
    {"endpoint": "ws://localhost:8282", "created_at": "...", "pid": 12345}
`pid` is only set for `launch`-owned sessions.

Name resolution (highest priority first): `-s` flag, `GODOT_LOCATOR_SESSION`
env var, `default`.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .errors import SessionNotFoundError
from .paths import sessions_dir

ENV_SESSION = "GODOT_LOCATOR_SESSION"
DEFAULT_NAME = "default"

# Constrain session names to safe filesystem chars across all three OSes.
# Reject paths separators, control chars, and anything Windows reserves.
_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Session:
    name: str
    endpoint: str
    created_at: str = field(default_factory=_utcnow_iso)
    pid: int | None = None

    def to_json(self) -> dict:
        d = {"endpoint": self.endpoint, "created_at": self.created_at}
        if self.pid is not None:
            d["pid"] = self.pid
        return d

    @classmethod
    def from_json(cls, name: str, payload: dict) -> Session:
        return cls(
            name=name,
            endpoint=str(payload["endpoint"]),
            created_at=str(payload.get("created_at", _utcnow_iso())),
            pid=int(payload["pid"]) if payload.get("pid") is not None else None,
        )


def validate_name(name: str) -> str:
    if not _NAME_RE.match(name):
        raise ValueError(
            f"invalid session name {name!r} — use letters, digits, '.', '_', '-' (max 64 chars)"
        )
    return name


def resolve_session_name(flag: str | None, env: dict[str, str] | None = None) -> str:
    """Apply the documented resolution order and return the resolved name."""
    env = env if env is not None else os.environ
    if flag:
        return validate_name(flag)
    env_name = env.get(ENV_SESSION)
    if env_name:
        return validate_name(env_name)
    return DEFAULT_NAME


class SessionStore:
    """File-backed store at `sessions_dir()`.

    Operations are intentionally simple — concurrent CLI invocations on the
    same session are rare, and the OS-level atomic rename (`os.replace`) is
    enough to keep the file consistent.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = root if root is not None else sessions_dir()

    def _path(self, name: str) -> Path:
        return self.root / f"{validate_name(name)}.json"

    def list(self) -> list[Session]:
        if not self.root.is_dir():
            return []
        out: list[Session] = []
        for p in sorted(self.root.glob("*.json")):
            try:
                payload = json.loads(p.read_text(encoding="utf-8"))
                out.append(Session.from_json(p.stem, payload))
            except (OSError, ValueError, KeyError):
                # Skip corrupt files rather than blowing up `list`. The user
                # can `sessions rm` them by name if needed.
                continue
        return out

    def get(self, name: str) -> Session:
        path = self._path(name)
        if not path.is_file():
            raise SessionNotFoundError(name)
        payload = json.loads(path.read_text(encoding="utf-8"))
        return Session.from_json(name, payload)

    def exists(self, name: str) -> bool:
        return self._path(name).is_file()

    def save(self, session: Session) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(session.name)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(session.to_json(), indent=2), encoding="utf-8")
        os.replace(tmp, path)

    def delete(self, name: str) -> bool:
        """Remove a session file. Returns True if it existed."""
        path = self._path(name)
        try:
            path.unlink()
            return True
        except FileNotFoundError:
            return False
