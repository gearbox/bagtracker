from fastapi import APIRouter, Depends, Response
from fastapi import status as status_code

from backend import managers, schemas

router = APIRouter()


@router.get(
    "/healthcheck",
    status_code=status_code.HTTP_200_OK,
)
def healthcheck(
    response: Response,
    healthcheck_manager: managers.HealthCheckManager = Depends(managers.HealthCheckManager),
) -> schemas.HealthCheckResponse:
    status_api = healthcheck_manager.get_api_status()
    status_db = healthcheck_manager.get_db_status()
    status_redis = healthcheck_manager.get_redis_status()
    status = bool(status_api.status and status_db.status and status_redis.status)
    if not status:
        response.status_code = status_code.HTTP_500_INTERNAL_SERVER_ERROR
    return schemas.HealthCheckResponse(
        status=status,
        status_api=status_api,
        status_db=status_db,
        status_redis=status_redis,
    )
