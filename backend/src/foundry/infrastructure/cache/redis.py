"""Redis connection management and caching utilities."""

import json
from typing import Any
from datetime import timedelta

import redis.asyncio as redis
from redis.asyncio import Redis

from foundry.config import settings

# Global Redis connection pool
_redis_pool: Redis | None = None


async def init_redis() -> None:
    """Initialize the Redis connection pool."""
    global _redis_pool

    _redis_pool = redis.from_url(
        str(settings.redis_url),
        encoding="utf-8",
        decode_responses=True,
        max_connections=settings.redis_pool_size,
    )


async def close_redis() -> None:
    """Close the Redis connection pool."""
    global _redis_pool

    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None


async def get_redis() -> Redis:
    """Get the Redis connection instance."""
    if _redis_pool is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis_pool


async def get_redis_health() -> dict:
    """
    Check Redis health status.

    Returns:
        Dictionary with health status information.
    """
    if _redis_pool is None:
        return {
            "healthy": False,
            "error": "Redis not initialized",
        }

    try:
        await _redis_pool.ping()
        info = await _redis_pool.info("memory")
        return {
            "healthy": True,
            "used_memory": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
        }
    except Exception as e:
        return {
            "healthy": False,
            "error": str(e),
        }


class RedisCache:
    """Redis caching utility class with common operations."""

    def __init__(self, redis_client: Redis, prefix: str = "foundry") -> None:
        self.redis = redis_client
        self.prefix = prefix
        self.default_ttl = settings.redis_cache_ttl

    def _make_key(self, key: str) -> str:
        """Create a prefixed cache key."""
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> Any | None:
        """Get a value from cache."""
        full_key = self._make_key(key)
        value = await self.redis.get(full_key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | timedelta | None = None,
    ) -> bool:
        """Set a value in cache."""
        full_key = self._make_key(key)

        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        if ttl is None:
            ttl = self.default_ttl
        elif isinstance(ttl, timedelta):
            ttl = int(ttl.total_seconds())

        return await self.redis.set(full_key, value, ex=ttl)

    async def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        full_key = self._make_key(key)
        result = await self.redis.delete(full_key)
        return result > 0

    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        full_key = self._make_key(key)
        return await self.redis.exists(full_key) > 0

    async def get_or_set(
        self,
        key: str,
        factory: Any,
        ttl: int | timedelta | None = None,
    ) -> Any:
        """Get value from cache or compute and set it."""
        value = await self.get(key)
        if value is not None:
            return value

        # Compute value
        if callable(factory):
            value = await factory() if hasattr(factory, "__await__") else factory()
        else:
            value = factory

        await self.set(key, value, ttl)
        return value

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching a pattern."""
        full_pattern = self._make_key(pattern)
        keys = []
        async for key in self.redis.scan_iter(match=full_pattern):
            keys.append(key)

        if keys:
            return await self.redis.delete(*keys)
        return 0

    # Hash operations for feature store
    async def hget(self, key: str, field: str) -> Any | None:
        """Get a field from a hash."""
        full_key = self._make_key(key)
        value = await self.redis.hget(full_key, field)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    async def hset(self, key: str, field: str, value: Any) -> bool:
        """Set a field in a hash."""
        full_key = self._make_key(key)
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        return await self.redis.hset(full_key, field, value)

    async def hmget(self, key: str, fields: list[str]) -> dict[str, Any]:
        """Get multiple fields from a hash."""
        full_key = self._make_key(key)
        values = await self.redis.hmget(full_key, fields)
        result = {}
        for field, value in zip(fields, values):
            if value is not None:
                try:
                    result[field] = json.loads(value)
                except json.JSONDecodeError:
                    result[field] = value
        return result

    async def hmset(self, key: str, mapping: dict[str, Any], ttl: int | None = None) -> bool:
        """Set multiple fields in a hash."""
        full_key = self._make_key(key)
        serialized = {}
        for field, value in mapping.items():
            if isinstance(value, (dict, list)):
                serialized[field] = json.dumps(value)
            else:
                serialized[field] = value

        await self.redis.hset(full_key, mapping=serialized)
        if ttl:
            await self.redis.expire(full_key, ttl)
        return True

    async def hgetall(self, key: str) -> dict[str, Any]:
        """Get all fields from a hash."""
        full_key = self._make_key(key)
        data = await self.redis.hgetall(full_key)
        result = {}
        for field, value in data.items():
            try:
                result[field] = json.loads(value)
            except json.JSONDecodeError:
                result[field] = value
        return result

    # Increment/decrement for rate limiting
    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment a counter."""
        full_key = self._make_key(key)
        return await self.redis.incrby(full_key, amount)

    async def decr(self, key: str, amount: int = 1) -> int:
        """Decrement a counter."""
        full_key = self._make_key(key)
        return await self.redis.decrby(full_key, amount)

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on a key."""
        full_key = self._make_key(key)
        return await self.redis.expire(full_key, ttl)

    async def ttl(self, key: str) -> int:
        """Get TTL of a key in seconds."""
        full_key = self._make_key(key)
        return await self.redis.ttl(full_key)
