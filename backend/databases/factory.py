from collections.abc import Iterator

from sqlalchemy.orm import Session

from backend.databases.base import BaseDatabase
from backend.databases.mariadb import MariaDatabase
from backend.databases.postgres import PostgresDatabase

_db_instance: BaseDatabase | None = None


def init_database(db_url: str, db_type: str, *, force_reinit: bool = False) -> BaseDatabase:
    """
    Factory + Singleton for database instance.

    - db_url: connection string
    - db_type: "postgres", "mariadb", etc.
    - force_reinit: if True, will rebuild instance (useful for tests)
    """
    global _db_instance

    if _db_instance is not None and not force_reinit:
        return _db_instance

    db_type = db_type.lower()

    if db_type in {"postgres", "postgresql"}:
        _db_instance = PostgresDatabase(db_url)
    elif db_type in {"maria", "mariadb"}:
        _db_instance = MariaDatabase(db_url)
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

    _db_instance.init_db()
    return _db_instance


def get_db_instance() -> BaseDatabase:
    """Return the already initialized DB instance (singleton)."""
    global _db_instance
    if _db_instance is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db_instance


# Dependency
def get_db_session() -> "Iterator[Session]":
    db = get_db_instance()
    with db.session() as session:
        yield session
