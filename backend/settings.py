from decimal import Decimal
from enum import Enum
from functools import lru_cache
from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict


class Web3Providers(str, Enum):
    LLAMARPC_ETH = "https://eth.llamarpc.com"
    LLAMARPC_BNB = "https://binance.llamarpc.com"
    LLAMARPC_BASE = "https://base.llamarpc.com"
    MAINNET = "https://mainnet.infura.io/v3/<API_KEY>"
    ROPSTEN = "https://ropsten.infura.io/v3/<API_KEY>"
    RINKEBY = "https://rinkeby.infura.io/v3/<API_KEY>"
    GOERLI = "https://goerli.infura.io/v3/<API_KEY>"
    KOVAN = "https://kovan.infura.io/v3/<API_KEY>"
    BSC_MAINNET = "https://bsc-dataseed.binance.org/"
    BSC_TESTNET = "https://data-seed-prebsc-1-s1.binance.org:8545/"
    POLYGON_MAINNET = "https://polygon-rpc.com/"
    POLYGON_TESTNET = "https://matic-testnet.rpc.thirdweb.com/"
    AVALANCHE_MAINNET = "https://api.avax.network/ext/bc/C/rpc"
    AVALANCHE_TESTNET = "https://api.avax-test.network/ext/bc/C/rpc"


class DBType(str, Enum):
    POSTGRESQL = "postgres"
    MARIADB = "mariadb"


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
    db_driver_async: str = "postgresql+asyncpg"
    db_driver_sync: str = "postgresql+psycopg"

    # Redis
    redis_host: str | None = None
    redis_port: int = 6379
    redis_db: int = 0
    redis_username: str | None = None
    redis_password: str | None = None

    # Taskiq
    taskiq_redis_url: str | None = None  # If not set, will be constructed from redis settings

    # Logging
    default_log_format: str = "[{time:%Y-%m-%d %H:%M:%S:%f %z}] - {name} - <level>{level}</level> - {message}"
    logging_level: str = "INFO"

    # Web3
    # "https://mainnet.infura.io/v3/<API_KEY>"
    web3_provider: str = Web3Providers.LLAMARPC_ETH
    infura_api_key: str | None = None

    # Etherscan API (for transaction syncing)
    etherscan_api_key: str | None = None  # Ethereum mainnet & testnets
    bscscan_api_key: str | None = None  # Binance Smart Chain
    polygonscan_api_key: str | None = None  # Polygon
    arbiscan_api_key: str | None = None  # Arbitrum
    optimism_etherscan_api_key: str | None = None  # Optimism
    basescan_api_key: str | None = None  # Base

    # Security settings START
    # Encryption
    encryption_key: str = "my encryption key, set in env"
    encryption_key_old: str | None = None  # for key rotation

    # security
    secret_key: str = "my secret key, set in env"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Telegram Bot Token for Mini App authentication
    telegram_bot_token: str | None = None

    # api keys rotation reminder (days)
    api_key_rotation_days: int = 90
    # Security settings END

    # App settings
    balance_dust_threshold: Decimal = Decimal("0.000001")
    balance_snapshot_enabled: bool = True
    balance_hourly_snapshots: bool = True
    balance_daily_snapshots: bool = True
    # Price update interval in seconds (default: 5 minutes).
    balance_price_update_interval: int = 300
    # Number of days to retain daily/weekly history.
    balance_history_retention_days: int = 90
    # Number of days to retain hourly snapshots.
    balance_hourly_retention_days: int = 7

    # Override settings with OS ENV values
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def db_url(self) -> str:
        """Sync database URL (for Alembic migrations)"""
        return (
            f"{self.db_driver_sync}://{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def async_db_url(self) -> str:
        """Async database URL (for application runtime)"""
        return (
            f"{self.db_driver_async}://{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def db_type(self) -> str:
        return DBType[self.db_driver_async.split("+")[0].upper()].value

    @property
    def redis_url(self) -> str:
        """Redis URL"""
        if self.taskiq_redis_url:
            return self.taskiq_redis_url

        user = getattr(self, "redis_username", None)
        password = getattr(self, "redis_password", None)
        host = self.redis_host
        port = self.redis_port
        db = self.redis_db

        auth_part = ""
        if user and password:
            auth_part = f"{quote(user)}:{quote(password)}@"
        elif password:
            auth_part = f":{quote(password)}@"
        elif user:
            auth_part = f"{quote(user)}@"

        return f"redis://{auth_part}{host}:{port}/{db}"


@lru_cache
def get_settings():
    """
    Dependency function for FastAPI to inject settings.

    Usage in route handlers:
        @router.get("/example")
        async def example(
            settings: Annotated[Settings, Depends(get_settings)]
        ):
            return {"threshold": settings.balance_dust_threshold}

    Usage in managers:
        class MyManager(BaseCRUDManager[Model]):
            def __init__(
                self,
                db,
                settings: Annotated[Settings, Depends(get_settings)]
            ):
                super().__init__(db)
                self.settings = settings

    The @lru_cache decorator ensures Settings is only instantiated once
    and reused across all requests (singleton pattern).
    """
    return Settings()


settings = get_settings()
