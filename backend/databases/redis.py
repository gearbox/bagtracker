import redis
from loguru import logger

from backend.settings import settings


def get_redis_client() -> redis.Redis:
    logger.info(f"Connecting to Redis at {settings.redis_host}:{settings.redis_port}")
    if not settings.redis_host:
        error_message = "Redis host is not set in settings"
        logger.error(error_message)
        raise RuntimeError(error_message)
    return redis.Redis(
        host=settings.redis_host, port=settings.redis_port, db=settings.redis_db, password=settings.redis_password
    )
