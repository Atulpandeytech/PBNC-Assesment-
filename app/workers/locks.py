import asyncio
import time
from typing import Optional
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.logging import logger

_lock_redis: Optional[aioredis.Redis] = None
_redis_checked = False


async def get_lock_redis() -> Optional[aioredis.Redis]:
    global _lock_redis, _redis_checked
    if _redis_checked:
        return _lock_redis
    if settings.REDIS_URL:
        try:
            r = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=0.5,
                socket_connect_timeout=0.5,
                retry_on_timeout=False,
            )
            await r.ping()
            _lock_redis = r
        except Exception as e:
            logger.warning(f"Redis unavailable for distributed locks: {e}")
            _lock_redis = None
    _redis_checked = True
    return _lock_redis


class RedisLock:
    """Distributed lock using Redis with automatic expiration."""

    def __init__(self, key: str, ttl_seconds: int = 300):
        self.key = f"lock:{key}"
        self.ttl = ttl_seconds
        self.token = str(time.time())
        self.acquired = False

    async def __aenter__(self):
        redis = await get_lock_redis()
        if not redis:
            # If Redis is unavailable in local testing, allow lock acquisition
            self.acquired = True
            return self

        # Try to acquire lock with SET NX EX
        res = await redis.set(self.key, self.token, nx=True, ex=self.ttl)
        self.acquired = bool(res)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if not self.acquired:
            return

        redis = await get_lock_redis()
        if not redis:
            return

        try:
            # Release lock only if token matches
            val = await redis.get(self.key)
            if val == self.token:
                await redis.delete(self.key)
        except Exception:
            pass
