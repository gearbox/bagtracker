import tomllib
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
from backend.databases import postgres
from backend.logger import init_logging
from backend.settings import settings


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
    postgres.init_postgres()
    yield
    # shutdown logic


def create_app() -> FastAPI:
    app = FastAPI(
        docs_url=None,
        lifespan=lifespan,
    )
    try:
        with open("pyproject.toml", mode="rb") as config:
            metadata = tomllib.load(config)
        app.version = metadata["project"]["version"]
    except Exception as e:
        logger.error(f"Failed to load project version from pyproject.toml: {e}")
    app.title = settings.app_name
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
