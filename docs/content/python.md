# Python client

`godot-locator-client` is the async WebSocket client used by the MCP server,
the CLI, and any other Python that wants to drive a running Godot game.

## Install

```sh
uv add godot-locator-client
```

## Usage

```python
import asyncio
from godot_locator_client import LocatorClient

async def main():
    client = LocatorClient(host="127.0.0.1", port=8282)
    try:
        snapshot = await client.call("snapshot")
        print(snapshot)
    finally:
        await client.close()

asyncio.run(main())
```

`call(method, **params)` is the only method you need — it serializes the
request, awaits the matching response, and either returns `result` or raises
`LocatorError` (for both transport failures and protocol-level errors).

## Connection lifecycle

The client connects lazily on the first `call` and keeps the socket open
across calls. If the socket drops mid-call, the next call transparently
reconnects.

## Error handling

```python
from godot_locator_client import LocatorError

try:
    await client.call("click", ref="e7")
except LocatorError as e:
    # Either the socket couldn't be reached, or the Godot side returned
    # `{"error": "..."}` — the message is in str(e).
    ...
```

<!-- TODO: list the methods the Godot side supports (snapshot, click, type, …). -->
