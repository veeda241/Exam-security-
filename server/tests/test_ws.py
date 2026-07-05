"""WebSocket hub tests."""
import pytest


@pytest.mark.asyncio
async def test_event_bus_publish():
    import fakeredis.aioredis

    from core.event_bus import EventBus

    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    bus = EventBus()
    bus._redis = fake

    await bus.publish("sess-1", {"type": "event", "session_id": "sess-1"})

    # Verify publish does not raise
    assert bus._redis is not None
