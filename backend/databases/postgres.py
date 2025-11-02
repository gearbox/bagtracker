from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool, QueuePool

from backend.databases.base import BaseAsyncDatabase, BaseDatabase


class PostgresDatabase(BaseDatabase):
    def init_db(self) -> None:
        logger.debug("Initializing Postgres database...")
        try:
            # TODO: Move pool settings to settings.py (and ENV)
            self.engine = create_engine(
                self.db_url,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,  # Verify connections before use
                pool_recycle=3600,  # Recycle connections after 1 hour
                echo=False,
                connect_args={
                    "connect_timeout": 10,
                    "application_name": "bagtracker",
                },
            )
            self.SessionLocal = sessionmaker(bind=self.engine)
            logger.info("✅ Postgres database initialized successfully")
        except Exception as e:
            logger.error(f"Postgres initialization failed: {e}")
            self.engine, self.SessionLocal = None, None


class AsyncPostgresDatabase(BaseAsyncDatabase):
    async def init_db(self) -> None:
        logger.debug("Initializing Async Postgres database...")
        try:
            self.engine = create_async_engine(
                self.db_url,
                poolclass=AsyncAdaptedQueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False,
                connect_args={
                    "server_settings": {
                        "application_name": "bagtracker",
                    },
                },
            )
            self.SessionLocal = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            logger.info("✅ Async Postgres database initialized successfully")
        except Exception as e:
            logger.error(f"Async Postgres initialization failed: {e}")
            self.engine, self.SessionLocal = None, None
