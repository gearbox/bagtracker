from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from backend.databases.base import BaseDatabase


class PostgresDatabase(BaseDatabase):
    def init_db(self) -> None:
        logger.debug("Initializing Postgres database...")
        try:
            # self.engine = create_engine(self.db_url)
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
