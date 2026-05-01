"""Error hierarchy. Session errors subclass `LocatorError` so a single
`except LocatorError` at the top level catches transport + session failures.
"""

from __future__ import annotations


class LocatorError(RuntimeError):
    """Transport or protocol failure talking to the runtime plugin."""


class SessionError(LocatorError):
    """Something is wrong with the session itself, not the wire."""


class SessionNotFoundError(SessionError):
    """Asked for a session name that has no file on disk."""

    def __init__(self, name: str) -> None:
        super().__init__(f"no session named '{name}' — run `attach` or `launch` first")
        self.name = name


class SessionStaleError(SessionError):
    """The session file pointed at an endpoint that's no longer reachable.

    Raised by the stale-detection wrapper after the file has been removed,
    so the CLI just needs to print and exit.
    """

    def __init__(self, name: str, endpoint: str) -> None:
        super().__init__(
            f"Session '{name}' is stale — {endpoint} is not reachable.\n"
            f"Godot game has exited. Session removed."
        )
        self.name = name
        self.endpoint = endpoint
