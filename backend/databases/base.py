from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager

from loguru import logger
from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
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
    def session(self) -> "Iterator[Session]":
        """Provide a database session context manager."""
        if self.SessionLocal is None:
            logger.error("Database session not initialized")
            raise RuntimeError("Database not initialized. Call init_db() first.")

        db: Session = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()


class BaseAsyncDatabase(ABC):
    """Abstract base class for all async databases."""

    def __init__(self, db_url: str) -> None:
        self.db_url = db_url
        self.engine: AsyncEngine | None = None
        self.SessionLocal: async_sessionmaker[AsyncSession] | None = None

    @abstractmethod
    async def init_db(self) -> None:
        """Initialize database connection (engine + session factory)."""
        pass

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Provide an async database session context manager."""
        if self.SessionLocal is None:
            logger.error("Async database session not initialized")
            raise RuntimeError("Async database not initialized. Call init_db() first.")

        async with self.SessionLocal() as db:
            try:
                yield db
            finally:
                await db.close()

    async def close(self) -> None:
        """Close database engine"""
        if self.engine:
            await self.engine.dispose()
