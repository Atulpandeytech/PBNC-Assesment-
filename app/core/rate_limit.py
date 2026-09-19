import time
from typing import Optional
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.errors import RateLimitExceededError
from app.core.logging import logger

_redis_client: Optional[aioredis.Redis] = None


async def get_redis_client() -> Optional[aioredis.Redis]:
    global _redis_client
    if _redis_client is None and settings.REDIS_URL:
        try:
            _redis_client = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0
            )
            await _redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis connection failed for rate limiter: {e}")
            _redis_client = None
    return _redis_client


async def check_rate_limit(key: str, limit: int = 120, window_seconds: int = 60) -> None:
    """Check rate limit using sliding window counter in Redis."""
    if not settings.RATE_LIMIT_ENABLED:
        return

    redis = await get_redis_client()
    if not redis:
        return

    try:
        current_time = int(time.time())
        window_key = f"ratelimit:{key}:{current_time // window_seconds}"
        current_count = await redis.incr(window_key)
        if current_count == 1:
            await redis.expire(window_key, window_seconds * 2)

        if current_count > limit:
            raise RateLimitExceededError(
                f"Rate limit of {limit} requests per {window_seconds}s exceeded. Please retry later.",
                details={"limit": limit, "window_seconds": window_seconds}
            )
    except RateLimitExceededError:
        raise
    except Exception as e:
        logger.warning(f"Rate limiting check failed; allowing request: {e}")
