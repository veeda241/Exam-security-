"""
ExamGuard Pro - Cache Utility
Redis caching decorator
"""

import json
import os
from functools import wraps
from typing import Callable, Any
import redis.asyncio as redis
from fastapi import Request, Response

# Redis Config
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ENABLE_CACHE = os.getenv("ENABLE_CACHE", "false").lower() == "true"

class CacheService:
    def __init__(self):
        self.redis = redis.from_url(REDIS_URL, decode_responses=True) if ENABLE_CACHE else None
        
    async def get(self, key: str) -> Any:
        if not self.redis: return None
        data = await self.redis.get(key)
        return json.loads(data) if data else None

    async def set(self, key: str, value: Any, ttl: int = 60):
        if not self.redis: return
        await self.redis.set(key, json.dumps(value), ex=ttl)

cache_service = CacheService()

def cache_response(ttl: int = 60):
    """
    Decorator to cache endpoint API responses
    Key strategy: route path + query params
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not ENABLE_CACHE:
                return await func(*args, **kwargs)
                
            # Extract Request object
            request = next((arg for arg in args if isinstance(arg, Request)), None)
            if not request:
                request = kwargs.get('request')
                
            if request:
                # Generate cache key
                key = f"cache:{request.url.path}:{request.query_params}"
                
                # Check cache
                cached = await cache_service.get(key)
                if cached:
                    return cached
                
                # Execute
                result = await func(*args, **kwargs)
                
                # Store
                # Need to handle Pydantic models serialization
                # For now assume dict or list return
                if isinstance(result, (dict, list)):
                     await cache_service.set(key, result, ttl)
                     
                return result
            return await func(*args, **kwargs)
        return wrapper
    return decorator
