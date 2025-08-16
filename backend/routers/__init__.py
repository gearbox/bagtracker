from fastapi import APIRouter

from backend.dependencies import common, token_auth
from backend.routers import healthcheck, info

main_router = APIRouter(dependencies=common)
main_router.include_router(healthcheck.router, tags=['Health check'])
main_router.include_router(info.router, tags=['info'], dependencies=token_auth)
