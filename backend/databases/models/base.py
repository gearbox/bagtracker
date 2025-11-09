import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Self, TypeVar

import sqlalchemy.exc
from loguru import logger
from sqlalchemy import BigInteger, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column, selectinload
from sqlalchemy.sql import func, select, text

from backend.errors import DatabaseError, UnexpectedException

T = TypeVar("T", bound="Base")


class DecimalEncoder(json.JSONEncoder):
    """
    JSON encoder that handles Decimal, datetime, and UUID types

    Usage example:
    ```
    def serialize_model_safe(model_instance) -> str:
        return json.dumps(model_instance.to_dict(), cls=DecimalEncoder, ensure_ascii=False)
    ```
    """

    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)  # Keep as string
        elif isinstance(o, datetime):
            return o.isoformat()
        elif isinstance(o, UUID):
            return str(o)
        return super().default(o)


class Base(DeclarativeBase):
    """
    Base model with dual ID strategy:
    - id (BigInteger): Internal use, database joins, foreign keys
    - uuid (UUID): External use, API exposure, frontend
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="Internal primary key for database operations"
    )

    # UUID for API/external use
    uuid: Mapped["uuid.UUID"] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        server_default=func.gen_random_uuid(),
        index=True,
        comment="External identifier for API and frontend",
    )

    memo: Mapped[str | None] = mapped_column(Text, nullable=True)  # optional user-defined memo/description
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # Who created the record
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # Who last updated

    @declared_attr.directive
    def __mapper_args__(cls):
        return {
            "eager_defaults": True,  # Fetch server defaults immediately
        }

    async def save(self, session: AsyncSession, by_user_id: int | None = None, log_action: str | None = None) -> None:
        if by_user_id:
            self.updated_by = by_user_id
        self.updated_at = datetime.now(UTC)
        try:
            session.add(self)
            await session.commit()
            await session.refresh(self)
        except sqlalchemy.exc.IntegrityError as e:
            await session.rollback()
            raise DatabaseError(status_code=500, exception_message=f"Database integrity error: {str(e)}") from e
        except sqlalchemy.exc.SQLAlchemyError as e:
            await session.rollback()
            raise DatabaseError(status_code=500, exception_message=f"Internal database error: {str(e)}") from e
        except Exception as e:
            await session.rollback()
            logger.exception("Unexpected exception occurred during save operation")
            raise UnexpectedException(exception_message=f"Internal server error: {str(e)}") from e
        else:
            if log_action:
                logger.info(log_action)

    async def delete(self, session: AsyncSession, by_user_id: int | None = None) -> None:
        """Soft delete instead of hard delete"""
        self.is_deleted = True
        await self.save(session, by_user_id, f"Delete record with ID: {self.id}")

    async def delete_hard(self, session: AsyncSession) -> None:
        """Hard delete - use with caution"""
        try:
            await session.delete(self)
            await session.commit()
        except sqlalchemy.exc.SQLAlchemyError as e:
            await session.rollback()
            raise DatabaseError(exception_message=f"Internal database error: {str(e)}") from e
        except Exception as e:
            await session.rollback()
            logger.exception("Unexpected exception occurred during delete operation")
            raise UnexpectedException(exception_message=f"Internal server error: {str(e)}") from e

    async def restore(self, session: AsyncSession, by_user_id: int | None = None) -> None:
        """Restore a soft-deleted record"""
        self.is_deleted = False
        await self.save(session, by_user_id, "Restore record with ID: {self.id}")

    def _assign_attributes(self, assign_dict: dict) -> None:
        for attribute, value in assign_dict.items():
            if hasattr(self, attribute):
                setattr(self, attribute, value)

    async def create(self, session: AsyncSession, create_dict: dict, by_user_id: int | None = None) -> Self:
        self._assign_attributes(create_dict)
        if by_user_id:
            self.created_by = by_user_id
        await self.save(session, by_user_id, "Creating new record")
        return self

    async def update(self, session: AsyncSession, update_dict: dict, by_user_id: int | None = None) -> Self:
        self._assign_attributes(update_dict)
        await self.save(session, by_user_id, "Updating record with ID: {self.id}")
        return self

    async def upsert(self, session: AsyncSession, upsert_dict: dict, by_user_id: int | None = None) -> Self:
        """
        Update existing record or create new one if it doesn't exist.
        If the instance has an ID, it updates; otherwise, it creates.
        """
        if self.id or self.uuid:
            return await self.update(session, upsert_dict, by_user_id)
        return await self.create(session, upsert_dict, by_user_id)

    @classmethod
    async def get_by_id(cls: type[T], session: AsyncSession, item_id: int, include_deleted: bool = False) -> T:
        """Get by internal BigInteger ID"""
        try:
            obj = await session.get_one(cls, item_id)
            if obj.is_deleted and not include_deleted:
                raise sqlalchemy.exc.NoResultFound()
            return obj
        except sqlalchemy.exc.NoResultFound:
            raise DatabaseError(404, "Object not found") from None
        except Exception as e:
            raise DatabaseError(500, f"Database error: {str(e)}") from e

    @classmethod
    async def get_by_uuid(
        cls: type[T],
        session: AsyncSession,
        item_uuid: "uuid.UUID",
        include_deleted: bool = False,
    ) -> T:
        """
        Get by UUID (for API use). Rises an error if no result found.
            :rises: :class:`DatabaseError`
        """
        return await cls.get_one(session, include_deleted, uuid=item_uuid)

    @classmethod
    async def get_one(
        cls: type[T],
        session: AsyncSession,
        include_deleted: bool = False,
        **kwargs,
    ) -> T:
        """
        Get one result or rise
            :rises: :class:`DatabaseError`
        """
        stmt = select(cls).filter_by(**kwargs)
        if not include_deleted:
            stmt = stmt.filter(cls.is_deleted.is_(False))
        result = await session.execute(stmt)
        try:
            return result.scalar_one()
        except sqlalchemy.exc.NoResultFound:
            raise DatabaseError(404, "Object not found") from None

    @classmethod
    async def get_all(
        cls: type[T], session: AsyncSession, include_deleted: bool = False, eager_load: list | None = None, **kwargs
    ) -> list[T]:
        stmt = select(cls).filter_by(**kwargs)
        if not include_deleted:
            stmt = stmt.filter(cls.is_deleted.is_(False))
        if eager_load:
            for relationship in eager_load:
                stmt = stmt.options(selectinload(relationship))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def sync_sequence(cls, session: AsyncSession, pk_field: str = "id") -> None:
        """
        Synchronize the db sequence for the given table's id column.

        Args:
            session: SQLAlchemy session object
            pk_field: The name of the ID column to synchronize (default is "id")
        """
        table_name = cls.__tablename__

        # Step 1: Get the sequence name
        sequence_name_query = text("SELECT pg_get_serial_sequence(:table_name, :pk_field)")
        result = await session.execute(sequence_name_query, {"table_name": table_name, "pk_field": pk_field})
        sequence_name = result.scalar()
        if not sequence_name:
            raise ValueError(f"No sequence found for {table_name}.{pk_field}")

        # Step 2: Get the maximum ID
        max_id_query = select(func.max(getattr(cls, pk_field)))
        result = await session.execute(max_id_query)
        max_id = result.scalar() or 0  # Default to 0 if table is empty

        # Step 3: Set the sequence to MAX(id) + 1
        alter_sequence_query = text(f"ALTER SEQUENCE {sequence_name} RESTART WITH {max_id + 1}")
        try:
            await session.execute(alter_sequence_query)
        except Exception as e:
            logger.warning(f"Could not set the sequence to MAX(id) + 1 = {max_id + 1}. Error: {str(e)}")
        else:
            await session.commit()

    def _serialize_value(self, value: Any, preserve_precision: bool = True) -> Any:
        """
        Safely serialize individual values

        Args:
            preserve_precision: If True, keeps Decimals as strings. If False, converts to float.
        """
        if value is None:
            return None
        elif isinstance(value, Decimal):
            return str(value) if preserve_precision else float(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, UUID):
            return str(value)
        elif isinstance(value, (list, dict)):
            return value  # Already JSON-serializable
        else:
            return value

    def to_dict(self, preserve_precision: bool = True, include_id: bool = False) -> dict[str, Any]:
        """
        Convert to dict - by default excludes internal 'id' field

        Args:
            preserve_precision: Keep Decimals as strings
            include_id: Include internal BigInteger ID (False by default for API safety)
        """
        return {
            column.name: self._serialize_value(getattr(self, column.name), preserve_precision)
            for column in self.__table__.columns
            if column.name != "id" and not include_id
        }

    def to_json(self, **kwargs) -> str:
        """Convert to JSON string with proper decimal handling"""
        return json.dumps(self.to_dict(), ensure_ascii=False, **kwargs)

    # For backward compatibility, keep the existing method name but improve it
    def to_schema(self, include_id: bool = False) -> dict[str, Any]:
        """Alias for to_dict() for backward compatibility"""
        return self.to_dict(include_id=include_id)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id}, uuid={self.uuid})>"
