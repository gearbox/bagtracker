from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from backend.databases.base import BaseAsyncDatabase
from backend.databases.postgres import AsyncPostgresDatabase

_db_instance: BaseAsyncDatabase | None = None


async def init_database(db_url: str, db_type: str, *, force_reinit: bool = False) -> BaseAsyncDatabase:
    """
    Factory + Singleton for async database instance.
    """
    global _db_instance

    if _db_instance is not None and not force_reinit:
        return _db_instance

    db_type = db_type.lower()

    if db_type in {"postgres", "postgresql"}:
        _db_instance = AsyncPostgresDatabase(db_url)
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

    await _db_instance.init_db()
    return _db_instance


def get_async_db_instance() -> BaseAsyncDatabase:
    """Return the already initialized DB instance (singleton)."""
    global _db_instance
    if _db_instance is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db_instance


async def get_async_db_session() -> AsyncIterator[AsyncSession]:
    """Async dependency for FastAPI"""
    db = get_async_db_instance()
    async with db.session() as session:
        yield session


async def close_async_database() -> None:
    """Close database connection"""
    global _db_instance
    if _db_instance:
        await _db_instance.close()
        _db_instance = None
