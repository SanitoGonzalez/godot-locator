"""Wire-level smoke test: connect, send a request, get a response."""

from client import Client


async def test_godot_responds_to_unknown_method(godot):
    async with Client(godot.port) as c:
        try:
            await c.call("definitely_not_a_method")
        except Exception as e:
            assert "unknown method" in str(e).lower()
        else:
            raise AssertionError("expected an error response")


async def test_snapshot_method_responds(godot):
    """Doesn't assert content yet — just that the wire round-trips."""
    async with Client(godot.port) as c:
        result = await c.call("snapshot")
        assert result is not None
