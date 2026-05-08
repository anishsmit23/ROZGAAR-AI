import redis.asyncio as aioredis

from app.config import settings

_redis_client = None


async def get_redis():
    global _redis_client
    if _redis_client is None:
        # redis.asyncio.from_url returns a client instance (not a coroutine),
        # so do not await it. Tests patch this function directly.
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis():
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
