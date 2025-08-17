from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Swagger
    openapi_url: str = "/openapi.json"
    swagger_ui_oauth2_redirect_url: str = "/docs/oauth2-redirect"

    # ASGI
    uvicorn_workers: int = 1
    bind_host: str = "0.0.0.0"
    bind_host_port: int = 80

    # Application
    app_name: str = "API"
    token_header_name: str = "header-name"
    token: str = "token"

    # Postgres
    postgres_host: str | None = None
    postgres_port: int = 5432
    postgres_db: str = "dbname"
    postgres_user: str = "user"
    postgres_password: str = "password"

    # Redis
    redis_host: str | None = None
    redis_port: int = 6379

    # Logging
    default_log_format: str = "[{time:%Y-%m-%d %H:%M:%S:%f %z}] - {name} - <level>{level}</level> - {message}"
    logging_level: str = "INFO"

    # Web3
    # "https://mainnet.infura.io/v3/<API_KEY>"
    web3_provider: str | None = None

    # Override settings with OS ENV values
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
