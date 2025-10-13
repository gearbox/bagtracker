from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request
from fastapi.concurrency import run_in_threadpool
from loguru import logger
from redis import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.databases import get_async_db_session, get_redis_client
from backend.schemas import HealthCheck
from backend.settings import settings


class HealthCheckManager:
    def __init__(
        self,
        request: Request,
        db: Annotated[AsyncSession, Depends(get_async_db_session)],
        redis_client: Annotated[Redis, Depends(get_redis_client)],
    ) -> None:
        self.db = db
        self.app = request.app
        self.redis_client = redis_client

    def _return_error(self, error_message, error):
        error_message = f"{error_message}{error}"
        logger.error(error_message)
        return HealthCheck(status=False, message=error_message)

    async def get_api_status(self) -> HealthCheck:
        try:
            start_time = self.app.state.start_time
            return HealthCheck(
                status=True,
                start_time=start_time,
                uptime_sec=int((datetime.now(UTC) - start_time).total_seconds()),
            )
        except Exception as e:
            return self._return_error("API healthcheck failed with error: ", e)

    async def get_db_status(self) -> HealthCheck:
        if not settings.postgres_host:
            return HealthCheck(status="Disabled", message="DB host is not set")
        try:
            await self.db.execute(select(1))
            return HealthCheck(status=True, message="DB healthcheck Ok")
        except Exception as e:
            return self._return_error("DB healthcheck failed: ", e)

    async def get_redis_status(self) -> HealthCheck:
        if not settings.redis_host:
            return HealthCheck(status="Disabled", message="Redis host is not set")
        try:
            await run_in_threadpool(self.redis_client.ping)
            return HealthCheck(status=True, message="Redis healthcheck Ok")
        except Exception as e:
            return self._return_error("Redis healthcheck failed: ", e)
