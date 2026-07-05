"""
Per-session rate limiting for event ingestion (Redis token bucket).
"""
from __future__ import annotations

import time
from typing import Optional

import redis

from config import settings

DEFAULT_MAX_EVENTS_PER_SECOND = 10
WINDOW_SECONDS = 1


class SessionRateLimiter:
    def __init__(
        self,
        redis_url: Optional[str] = None,
        max_per_second: int = DEFAULT_MAX_EVENTS_PER_SECOND,
    ):
        self._redis_url = redis_url or settings.REDIS_URL
        self._max = max_per_second
        self._client: Optional[redis.Redis] = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(self._redis_url, decode_responses=True)
        return self._client

    def allow(self, session_id: str) -> bool:
        key = f"ratelimit:events:{session_id}"
        now = int(time.time())
        pipe = self.client.pipeline()
        pipe.incr(key)
        pipe.expire(key, WINDOW_SECONDS)
        count, _ = pipe.execute()
        return int(count) <= self._max


_rate_limiter: Optional[SessionRateLimiter] = None


def get_rate_limiter() -> SessionRateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = SessionRateLimiter()
    return _rate_limiter
