import redis.asyncio as redis
from bot.config import config

redis_client = redis.from_url(config.redis_url, decode_responses=True)

async def get_cached_file_id(url: str) -> str | None:
    """Returns comma-separated file_ids for a given URL hash/link"""
    return await redis_client.get(f"media_cache:{url}")

async def set_cached_file_id(url: str, file_ids: str):
    """Caches comma-separated file_ids for 30 days"""
    await redis_client.set(f"media_cache:{url}", file_ids, ex=86400 * 30)
