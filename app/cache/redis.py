import redis.asyncio as aioredis

from app.config import get_settings

_redis_client = None


async def get_redis():
    global _redis_client
    if _redis_client is None:
        # redis.asyncio.from_url returns a client instance (not a coroutine),
        # so do not await it. Tests patch this function directly.
        settings = get_settings()
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis():
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
