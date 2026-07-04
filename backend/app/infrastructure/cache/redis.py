"""
Redis cache client for caching and session management.

Provides:
- Analysis result caching
- Session storage
- Rate limiting counters
"""

import json
from typing import Any, Optional

import redis.asyncio as redis

from app.core.config import get_settings

settings = get_settings()

_client: Optional[redis.Redis] = None


def init_redis() -> None:
    """Initialize Redis connection."""
    global _client

    _client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        decode_responses=True,
    )


def get_redis_client() -> redis.Redis:
    """Get the Redis client instance."""
    if _client is None:
        init_redis()
    return _client


async def close_redis() -> None:
    """Close Redis connection."""
    global _client
    if _client:
        await _client.close()
        _client = None


class CacheService:
    """
    Service for caching analysis results and other data.

    Provides TTL-based caching with automatic serialization.
    """

    def __init__(self, client: Optional[redis.Redis] = None):
        self.client = client or get_redis_client()

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception:
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 86400,  # 24 hours default
    ) -> bool:
        """Set a value in cache with TTL."""
        try:
            serialized = json.dumps(value, default=str)
            await self.client.setex(key, ttl_seconds, serialized)
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        try:
            await self.client.delete(key)
            return True
        except Exception:
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        try:
            return await self.client.exists(key) > 0
        except Exception:
            return False

    async def increment(self, key: str, ttl_seconds: int = 60) -> int:
        """Increment a counter with TTL."""
        try:
            pipe = self.client.pipeline()
            pipe.incr(key)
            pipe.expire(key, ttl_seconds)
            results = await pipe.execute()
            return results[0]
        except Exception:
            return 0
