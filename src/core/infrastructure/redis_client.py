from functools import lru_cache

from redis.asyncio import Redis, from_url

from src.core.config import settings


@lru_cache
def get_redis() -> Redis:
    return from_url(
        settings.redis_url,
        decode_responses=True,
    )
