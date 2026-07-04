"""Cache module initialization."""

from .redis import get_redis_client, init_redis

__all__ = ["get_redis_client", "init_redis"]
