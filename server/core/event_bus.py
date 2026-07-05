"""
Redis pub/sub event bus for session-scoped realtime updates.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator, Callable, Optional

import redis.asyncio as aioredis
from loguru import logger

from config import settings

CHANNEL_PREFIX = "session:"


class EventBus:
    def __init__(self, redis_url: Optional[str] = None):
        self._redis_url = redis_url or settings.REDIS_URL
        self._redis: Optional[aioredis.Redis] = None
        self._pubsub: Optional[aioredis.client.PubSub] = None
        self._listener_task: Optional[asyncio.Task] = None
        self._handlers: list[Callable[[str, dict[str, Any]], Any]] = []

    async def connect(self) -> None:
        if self._redis is None:
            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
            await self._redis.ping()

    async def disconnect(self) -> None:
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None
        if self._pubsub:
            await self._pubsub.close()
            self._pubsub = None
        if self._redis:
            await self._redis.close()
            self._redis = None

    async def publish(self, session_id: str, message: dict[str, Any]) -> None:
        await self.connect()
        channel = f"{CHANNEL_PREFIX}{session_id}"
        payload = json.dumps(message)
        await self._redis.publish(channel, payload)

    def subscribe(self, handler: Callable[[str, dict[str, Any]], Any]) -> None:
        self._handlers.append(handler)

    async def start_listener(self) -> None:
        await self.connect()
        self._pubsub = self._redis.pubsub()
        await self._pubsub.psubscribe(f"{CHANNEL_PREFIX}*")

        async def _listen() -> None:
            assert self._pubsub is not None
            async for raw in self._pubsub.listen():
                if raw["type"] not in ("pmessage", "message"):
                    continue
                channel = raw.get("channel", "")
                if isinstance(channel, bytes):
                    channel = channel.decode()
                session_id = channel.replace(CHANNEL_PREFIX, "")
                try:
                    data = json.loads(raw["data"])
                except (json.JSONDecodeError, TypeError):
                    continue
                for handler in self._handlers:
                    try:
                        result = handler(session_id, data)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as exc:
                        logger.error(f"EventBus handler error: {exc}")

        self._listener_task = asyncio.create_task(_listen())

    async def iter_messages(self) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        """Async generator for testing."""
        await self.connect()
        pubsub = self._redis.pubsub()
        await pubsub.psubscribe(f"{CHANNEL_PREFIX}*")
        try:
            async for raw in pubsub.listen():
                if raw["type"] not in ("pmessage", "message"):
                    continue
                channel = raw.get("channel", "")
                if isinstance(channel, bytes):
                    channel = channel.decode()
                session_id = channel.replace(CHANNEL_PREFIX, "")
                try:
                    data = json.loads(raw["data"])
                    yield session_id, data
                except (json.JSONDecodeError, TypeError):
                    continue
        finally:
            await pubsub.close()


_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
