from loguru import logger
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from backend.databases.base import BaseDatabase


class MariaDatabase(BaseDatabase):
    def init_db(self) -> None:
        logger.debug(f"Initializing MariaDB database...")
        try:
            self.engine = create_engine(self.db_url)
            self.SessionLocal = sessionmaker(bind=self.engine)
            logger.info("MariaDB database initialized successfully")
        except Exception as e:
            logger.error(f"MariaDB initialization failed: {e}")
            self.engine, self.SessionLocal = None, None
