from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class HealthCheck(BaseModel):
    status: Literal[True, False, "Disabled"] = True
    start_time: datetime | None = None
    uptime_sec: int | None = None
    message: str = "Healthcheck Ok"


class HealthCheckResponse(BaseModel):
    status: bool
    status_api: HealthCheck
    status_db: HealthCheck
    status_redis: HealthCheck
