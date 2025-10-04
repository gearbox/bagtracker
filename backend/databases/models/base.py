import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Self, TypeVar

import sqlalchemy.exc
from loguru import logger
from sqlalchemy import BigInteger, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, Query, Session, declared_attr, mapped_column
from sqlalchemy.sql import func, select, text

from backend.errors import DatabaseError, UnexpectedException

T = TypeVar("T", bound="Base")


# Custom JSON encoder for handling Decimal and other types
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

    # Primary key - BigInteger for performance
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
    )  # For API lookups

    # Common fields
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

    @classmethod
    def query_active(cls: type[T], session: Session) -> Query:
        """Query only active (non-deleted) records"""
        return session.query(cls).filter(cls.is_deleted == False)  # noqa: E712

    @classmethod
    def query_with_deleted(cls: type[T], session: Session) -> Query:
        """Query all records including soft-deleted ones"""
        return session.query(cls)

    def save(self, session: Session, by_user_id: int | None = None, log_action: str | None = None) -> None:
        if by_user_id:
            self.updated_by = by_user_id
        self.updated_at = datetime.now(UTC)
        try:
            session.add(self)
            session.commit()
        except sqlalchemy.exc.IntegrityError as e:
            raise DatabaseError(status_code=500, exception_message=f"Database integrity error: {str(e)}") from e
        except sqlalchemy.exc.SQLAlchemyError as e:
            raise DatabaseError(status_code=500, exception_message=f"Internal database error: {str(e)}") from e
        except Exception as e:
            logger.exception("Unexpected exception occurred during save operation")
            raise UnexpectedException(exception_message=f"Internal server error: {str(e)}") from e
        else:
            if log_action:
                logger.info(log_action)

    def delete(self, session: Session, by_user_id: int | None = None) -> None:
        """Soft delete instead of hard delete"""
        self.is_deleted = True
        self.save(session, by_user_id, f"Delete record with ID: {self.id}")

    def delete_hard(self, session: Session) -> None:
        """Hard delete - use with caution"""
        try:
            session.delete(self)
            session.commit()
        except sqlalchemy.exc.SQLAlchemyError as e:
            raise DatabaseError(exception_message=f"Internal database error: {str(e)}") from e
        except Exception as e:
            logger.exception("Unexpected exception occurred during delete operation")
            raise UnexpectedException(exception_message=f"Internal server error: {str(e)}") from e

    def restore(self, session: Session, by_user_id: int | None = None) -> None:
        """Restore a soft-deleted record"""
        self.is_deleted = False
        self.save(session, by_user_id, "Restore record with ID: {self.id}")

    def _assign_attributes(self, assign_dict: dict) -> None:
        for attribute, value in assign_dict.items():
            if hasattr(self, attribute):
                setattr(self, attribute, value)

    # TODO: Do we really need this method?
    @classmethod
    def _create_for_cls(cls: type[T], session: Session, create_dict: dict, by_user_id: int | None = None) -> T:
        if by_user_id:
            create_dict["created_by"] = by_user_id
        instance = cls(**create_dict)
        session.add(instance)
        session.commit()
        session.refresh(instance)
        return instance

    def create(self, session: Session, create_dict: dict, by_user_id: int | None = None) -> Self:
        self._assign_attributes(create_dict)
        if by_user_id:
            self.created_by = by_user_id
        self.save(session, by_user_id, "Creating new record")
        return self

    def update(self, session: Session, update_dict: dict, by_user_id: int | None = None) -> Self:
        self._assign_attributes(update_dict)
        self.save(session, by_user_id, "Updating record with ID: {self.id}")
        return self

    def upsert(self, session: Session, upsert_dict: dict, by_user_id: int | None = None) -> Self:
        """
        Update existing record or create new one if it doesn't exist.
        If the instance has an ID, it updates; otherwise, it creates.
        """
        if self.id or self.uuid:
            return self.update(session, upsert_dict, by_user_id)
        return self.create(session, upsert_dict, by_user_id)

    @classmethod
    def get_by_id(cls: type[T], session: Session, item_id: int, include_deleted: bool = False) -> T:
        """Get by internal BigInteger ID"""
        try:
            obj = session.get_one(cls, item_id)
            if obj.is_deleted and not include_deleted:
                raise sqlalchemy.exc.NoResultFound()
            return obj
        except sqlalchemy.exc.NoResultFound:
            raise DatabaseError(404, "Object not found") from None

    @classmethod
    def get_by_uuid(cls: type[T], session: Session, item_uuid: "uuid.UUID", include_deleted: bool = False) -> T:
        """Get by UUID (for API use)"""
        # query = cls.query_all(session) if include_deleted else cls.query_active(session)
        # try:
        #     return query.filter(cls.uuid == item_uuid).one()
        # except NoResultFound:
        #     raise DatabaseError(404, "Object not found") from None
        return cls.get_one(session, include_deleted, uuid=item_uuid)

    @classmethod
    def get_one(cls: type[T], session: Session, include_deleted: bool = False, **kwargs) -> T:
        query = cls.query_with_deleted(session) if include_deleted else cls.query_active(session)
        try:
            return query.filter_by(**kwargs).one()
        except sqlalchemy.exc.NoResultFound:
            raise DatabaseError(404, "Object not found") from None

    @classmethod
    def get_all(cls: type[T], session: Session, include_deleted: bool = False, **kwargs) -> list[T]:
        query = cls.query_with_deleted(session) if include_deleted else cls.query_active(session)
        return query.filter_by(**kwargs).all()

    @classmethod
    def sync_sequence(cls, session: Session, pk_field: str = "id") -> None:
        """
        Synchronize the db sequence for the given table's id column.

        Args:
            session: SQLAlchemy session object
            id_column: The name of the ID column to synchronize (default is "id")
        """
        table_name = cls.__tablename__

        # Step 1: Get the sequence name
        sequence_name_query = text("SELECT pg_get_serial_sequence(:table_name, :id_column)")
        sequence_name = session.execute(sequence_name_query, {"table_name": table_name, "id_column": pk_field}).scalar()
        if not sequence_name:
            raise ValueError(f"No sequence found for {table_name}.{pk_field}")

        # Step 2: Get the maximum ID
        max_id_query = select(func.max(getattr(cls, pk_field)))
        max_id = session.execute(max_id_query).scalar() or 0  # Default to 0 if table is empty

        # Step 3: Set the sequence to MAX(id) + 1
        alter_sequence_query = text(f"ALTER SEQUENCE {sequence_name} RESTART WITH :next_id")
        session.execute(alter_sequence_query, {"next_id": max_id + 1})
        session.commit()  # Commit the sequence change

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
