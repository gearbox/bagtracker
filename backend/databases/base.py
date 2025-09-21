from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager

from loguru import logger
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker


class BaseDatabase(ABC):
    """Abstract base class for all databases."""

    def __init__(self, db_url: str) -> None:
        self.db_url = db_url
        self.engine: Engine | None = None
        self.SessionLocal: sessionmaker | None = None

    @abstractmethod
    def init_db(self) -> None:
        """Initialize database connection (engine + session factory)."""
        pass

    @contextmanager
    def session(self) -> 'Iterator[Session]':
        """Provide a database session context manager."""
        if self.SessionLocal is None:
            logger.error("Database session not initialized")
            raise RuntimeError("Database not initialized. Call init_db() first.")

        db: Session = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
