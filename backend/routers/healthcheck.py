from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi import status as status_code

from backend import schemas
from backend.managers import HealthCheckManager

router = APIRouter()


@router.get(
    "/healthcheck",
    status_code=status_code.HTTP_200_OK,
)
async def healthcheck(
    response: Response,
    healthcheck_manager: Annotated[HealthCheckManager, Depends(HealthCheckManager)],
) -> schemas.HealthCheckResponse:
    status_api = await healthcheck_manager.get_api_status()
    status_db = await healthcheck_manager.get_db_status()
    status_redis = await healthcheck_manager.get_redis_status()
    status = bool(status_api.status and status_db.status and status_redis.status)
    if not status:
        response.status_code = status_code.HTTP_500_INTERNAL_SERVER_ERROR
    return schemas.HealthCheckResponse(
        status=status,
        status_api=status_api,
        status_db=status_db,
        status_redis=status_redis,
    )
