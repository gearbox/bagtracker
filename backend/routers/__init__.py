from fastapi import APIRouter

from backend.dependencies import common, token_auth
from backend.routers import healthcheck, info, eth

main_router = APIRouter(dependencies=common)
main_router.include_router(healthcheck.router, tags=['Health check'])
main_router.include_router(info.router, tags=['info'], dependencies=token_auth)
main_router.include_router(eth.router, tags=['Ethereum'],
    # Use the current module's name to dynamically set the router's prefix
    # __name__.replace("routers", "routers.eth").replace("__init__", "eth").router,
    # tags=['Ethereum'],
    # prefix="/eth",
)
