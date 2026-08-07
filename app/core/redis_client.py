from typing import AsyncGenerator
import redis.asyncio as redis

from app.core.config import settings

redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True
)


def get_redis_client() -> redis.Redis:
    """Get Redis client instance using the connection pool."""
    return redis.Redis(connection_pool=redis_pool)


async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """FastAPI dependency generator yielding an async Redis connection."""
    client = get_redis_client()
    try:
        yield client
    finally:
        await client.close()
