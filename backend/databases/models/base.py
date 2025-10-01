import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Self, TypeVar

from loguru import logger
from sqlalchemy import BigInteger, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.sql import func, select, text

from backend.errors import DatabaseError

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
    created_by: Mapped[int | None] = mapped_column(UUID(as_uuid=True), nullable=True)  # Who created the record
    updated_by: Mapped[int | None] = mapped_column(UUID(as_uuid=True), nullable=True)  # Who last updated

    def save(self, session: Session, commit: bool = True) -> None:
        session.add(self)
        if commit:
            session.commit()

    def delete(self, session: Session, by_user_id: int | None = None) -> None:
        """Soft delete instead of hard delete"""
        self.is_deleted = True
        if by_user_id:
            self.updated_by = by_user_id
        self.updated_at = datetime.now(UTC)
        self.save(session)

    def delete_hard(self, session: Session) -> None:
        """Hard delete - use with caution"""
        session.delete(self)
        session.commit()

    @classmethod
    def get_by_id(cls: type[T], session: Session, item_id: int, include_deleted: bool = False) -> T:
        """Get by internal BigInteger ID"""
        try:
            obj = session.get_one(cls, item_id)
            if obj.is_deleted and not include_deleted:
                raise DatabaseError(404, "Object not found")
            return obj
        except NoResultFound:
            raise DatabaseError(404, "Object not found") from None

    @classmethod
    def get_by_uuid(cls: type[T], session: Session, item_uuid: "uuid.UUID", include_deleted: bool = False) -> T:
        """Get by UUID (for API use)"""
        query = session.query(cls).filter(cls.uuid == item_uuid)
        if not include_deleted:
            query = query.filter(cls.is_deleted == False)  # noqa: E712
        try:
            return query.one()
        except NoResultFound:
            raise DatabaseError(404, "Object not found") from None

    @classmethod
    def get_one_by_kwargs(cls: type[T], session: Session, include_deleted: bool = False, **kwargs) -> T:
        query = session.query(cls).filter_by(**kwargs)
        if not include_deleted:
            query = query.filter(cls.is_deleted == False)  # noqa: E712
        try:
            return query.one()
        except NoResultFound:
            raise DatabaseError(404, "Object not found") from None

    @classmethod
    def get_many_by_kwargs(cls: type[T], session: Session, include_deleted: bool = False, **kwargs) -> list[T]:
        query = session.query(cls).filter_by(**kwargs)
        if not include_deleted:
            query = query.filter(cls.is_deleted == False)  # noqa: E712
        return query.all()

    @classmethod
    def get_all(cls, session: Session, include_deleted: bool = False) -> list:
        query = session.query(cls)
        if not include_deleted:
            query = query.filter(cls.is_deleted == False)  # noqa: E712
        return query.all()

    # TODO: Do we really need this method?
    @classmethod
    def create_for_cls(cls: type[T], session: Session, create_dict: dict, by_user_id: int | None = None) -> T:
        if by_user_id:
            create_dict["created_by"] = by_user_id
        instance = cls(**create_dict)
        session.add(instance)
        session.commit()
        session.refresh(instance)
        return instance

    def _assign_attributes(self, assign_dict: dict) -> None:
        for attribute, value in assign_dict.items():
            if hasattr(self, attribute):
                setattr(self, attribute, value)

    def create(self, session: Session, create_dict: dict, by_user_id: int | None = None, commit: bool = True) -> Self:
        self._assign_attributes(create_dict)
        if by_user_id:
            self.created_by = by_user_id
        self.save(session, commit)
        if commit:
            session.refresh(self)
        return self

    def update(self, session: Session, update_dict: dict, by_user_id: int | None = None, commit: bool = True) -> Self:
        self._assign_attributes(update_dict)
        if by_user_id:
            self.updated_by = by_user_id
        self.updated_at = datetime.now(UTC)
        self.save(session, commit)
        return self

    def upsert(self, session: Session, upsert_dict: dict, by_user_id: int | None = None, commit: bool = True) -> Self:
        """
        Update existing record or create new one if it doesn't exist.
        If the instance has an ID, it updates; otherwise, it creates.
        """
        if self.id or self.uuid:
            logger.info("Updating record")
            return self.update(session, upsert_dict, by_user_id, commit)
        logger.info("Creating record")
        self.create(session, upsert_dict, by_user_id, commit)
        return self

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
