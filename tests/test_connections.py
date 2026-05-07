from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_redis_set_get():
    with patch("redis.asyncio.from_url") as mock_redis:
        mock_client = AsyncMock()
        mock_client.get.return_value = "rozgaar"
        mock_redis.return_value = mock_client
        from app.cache.redis import close_redis, get_redis

        await close_redis()
        r = await get_redis()
        val = await r.get("test")
        assert val == "rozgaar"
        await close_redis()


def test_minio_ensure_bucket():
    with patch("minio.Minio.bucket_exists", return_value=False), \
         patch("minio.Minio.make_bucket") as mock_make:
        from app.storage.minio import ensure_bucket

        ensure_bucket()
        mock_make.assert_called_once()
