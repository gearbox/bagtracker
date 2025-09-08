from functools import lru_cache
from enum import Enum

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
    db_driver: str = "postgresql+psycopg2"

    # Redis
    redis_host: str | None = None
    redis_port: int = 6379

    # Logging
    default_log_format: str = "[{time:%Y-%m-%d %H:%M:%S:%f %z}] - {name} - <level>{level}</level> - {message}"
    logging_level: str = "INFO"

    # Web3
    # "https://mainnet.infura.io/v3/<API_KEY>"
    web3_provider: str = Web3Providers.LLAMARPC_ETH
    infura_api_key: str | None = None

    # Override settings with OS ENV values
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def db_url(self) -> str:
        return (
            f"{self.db_driver}://{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def db_type(self) -> str:
        return DBType[self.db_driver.split("+")[0].upper()].value


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
