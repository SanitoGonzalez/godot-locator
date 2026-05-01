"""Async glue + session-stale detection for CLI commands.

`with_session()` is the single place that enforces the spec's stale-cleanup
contract: on transport failure, drop the session file and re-raise as
`SessionStaleError` for the top-level handler.
"""

from __future__ import annotations

import asyncio
import functools
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from godot_locator_core import (
    LocatorClient,
    LocatorError,
    Session,
    SessionStaleError,
    SessionStore,
    resolve_session_name,
)


def _looks_like_unreachable(err: LocatorError) -> bool:
    """Distinguish 'transport dead' from 'method-level error'.

    The wire surfaces both as `LocatorError`. Stale-cleanup must only fire
    on the transport variants — otherwise a single bad command could nuke
    a perfectly healthy session.
    """
    msg = str(err).lower()
    return "can't reach" in msg or "closed mid-call" in msg


@asynccontextmanager
async def with_session(
    name_flag: str | None,
    *,
    store: SessionStore | None = None,
) -> AsyncIterator[tuple[Session, LocatorClient]]:
    """Yield `(session, client)`. On transport failure, drop the session
    file and re-raise as `SessionStaleError`."""
    store = store if store is not None else SessionStore()
    name = resolve_session_name(name_flag)
    session = store.get(name)
    client = LocatorClient.from_endpoint(session.endpoint)
    try:
        yield session, client
    except LocatorError as e:
        if _looks_like_unreachable(e):
            store.delete(session.name)
            raise SessionStaleError(session.name, session.endpoint) from e
        raise
    finally:
        await client.close()


def coro_command(fn: Callable[..., Awaitable[Any]]) -> Callable[..., Any]:
    """Wrap an async Click callback so Click can call it synchronously."""

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return asyncio.run(fn(*args, **kwargs))

    return wrapper
