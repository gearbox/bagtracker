import redis
from loguru import logger

from backend.settings import settings


def get_client() -> redis.Redis:
    logger.info(f"Connecting to Redis at {settings.redis_host}:{settings.redis_port}")
    return redis.Redis(host=settings.redis_host, port=settings.redis_port, db=0)
