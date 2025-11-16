from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.staticfiles import StaticFiles
from loguru import logger

from backend import errors, routers
from backend.databases.factory_async import close_async_database, init_database
from backend.logger import init_logging
from backend.security.encryption import init_encryption
from backend.settings import settings
from backend.taskiq_broker import broker


# noinspection PyUnusedLocal
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager.
    This function is called when the application starts and stops.
    """
    # startup logic
    app.state.start_time = datetime.now(UTC)
    init_logging()
    init_encryption()
    await init_database(settings.async_db_url, settings.db_type)

    # Start Taskiq broker
    logger.info("Starting Taskiq broker...")
    if not broker.is_worker_process:
        await broker.startup()
    logger.info("Taskiq broker started")

    yield

    # shutdown logic
    logger.info("Shutting down Taskiq broker...")
    if not broker.is_worker_process:
        await broker.shutdown()
    logger.info("Taskiq broker shut down")

    await close_async_database()


def get_app_version() -> str:
    """
    Get application version from generated version file.
    Falls back to environment variable or default.
    """
    try:
        from backend._version import __version__

        return __version__
    except ImportError:
        logger.warning("Version file not found, using fallback")
        return "0.0.0-dev"


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=get_app_version(),
        docs_url=None,
        lifespan=lifespan,
    )
    logger.info(f"🚀 Starting {app.title} v{app.version}")

    app.include_router(routers.main_router)
    app.add_exception_handler(Exception, errors.handle_exception)

    app.swagger_ui_oauth2_redirect_url = settings.swagger_ui_oauth2_redirect_url
    app.openapi_url = settings.openapi_url
    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/", include_in_schema=False)
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url or "/openapi.json",
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url="/static/openapi/swagger-ui-bundle.js",
            swagger_css_url="/static/openapi/swagger-ui.css",
            swagger_favicon_url="/static/openapi/favicon.png",
        )

    @app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
    async def swagger_ui_redirect():
        return get_swagger_ui_oauth2_redirect_html()

    @app.get("/redoc", include_in_schema=False)
    async def redoc_html():
        return get_redoc_html(
            openapi_url=app.openapi_url or "/openapi.json",
            title=f"{app.title} - ReDoc",
            redoc_js_url="/static/openapi/redoc.standalone.js",
        )

    return app
