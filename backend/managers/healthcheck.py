from datetime import UTC, datetime

from fastapi import Depends, Request
from loguru import logger
from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from backend.databases import get_db_session, get_redis_client
from backend.schemas import APIHealthCheck, DBHealthCheck
from backend.settings import settings


class HealthCheckManager:
    def __init__(
        self,
        request: Request,
        db: DBSession = Depends(get_db_session),
        redis_client: Redis = Depends(get_redis_client),
    ) -> None:
        self.db = db
        self.app = request.app
        self.redis_client = redis_client

    def get_api_status(self) -> APIHealthCheck:
        try:
            start_time = self.app.state.start_time
            return APIHealthCheck(
                status=True,
                start_time=start_time,
                uptime_sec=int((datetime.now(UTC) - start_time).total_seconds()),
            )
        except Exception as e:
            error_message = f"API healthcheck failed with error: {e}"
            logger.error(error_message)
            return APIHealthCheck(status=False, message=error_message)

    def get_db_status(self) -> DBHealthCheck:
        if not settings.postgres_host:
            return DBHealthCheck(status="Disabled", message="DB host is not set")
        try:
            self.db.execute(select(1))
            return DBHealthCheck(status=True, message="DB healthcheck Ok")
        except Exception as e:
            error_message = f"DB healthcheck failed: {e}"
            logger.error(error_message)
            return DBHealthCheck(status=False, message=error_message)

    def get_redis_status(self) -> DBHealthCheck:
        if not settings.redis_host:
            return DBHealthCheck(status="Disabled", message="Redis host is not set")
        try:
            self.redis_client.ping()
            return DBHealthCheck(status=True, message="Redis healthcheck Ok")
        except Exception as e:
            error_message = f"Redis healthcheck failed: {e}"
            logger.error(error_message)
            return DBHealthCheck(status=False, message=error_message)
