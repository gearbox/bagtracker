import uuid
from typing import Self, TypeVar

from sqlalchemy import Boolean, Column, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.sql import func, select, text

from backend.errors import DatabaseError

T = TypeVar("T", bound="Base")


class Base(DeclarativeBase):
    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    memo = Column(Text, nullable=True)  # optional user-defined memo/description
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="false")

    def save(self, session: Session, commit: bool = True) -> None:
        session.add(self)
        if commit:
            session.commit()

    def delete(self, session: Session) -> None:
        session.delete(self)
        session.commit()

    @classmethod
    def get(cls: type[T], session: Session, item_id: uuid.UUID | int) -> T:
        try:
            return session.get_one(cls, item_id)
        except NoResultFound:
            raise DatabaseError(404, "Object not found") from None

    @classmethod
    def get_one_by_kwargs(cls: type[T], session: Session, **kwargs) -> T:
        try:
            return session.query(cls).filter_by(**kwargs).one()
        except NoResultFound:
            raise DatabaseError(404, "Object not found") from None

    @classmethod
    def get_many_by_kwargs(cls: type[T], session: Session, **kwargs) -> list[T]:
        return session.query(cls).filter_by(**kwargs).all()

    @classmethod
    def get_all(cls, session: Session) -> list:
        return session.query(cls).all()

    @classmethod
    def create(cls: type[T], session: Session, create_dict: dict) -> T:
        instance = cls(**create_dict)
        session.add(instance)
        session.commit()
        return instance

    def update(self, session: Session, update_dict: dict, commit: bool = True) -> Self:
        for attribute, value in update_dict.items():
            if hasattr(self, attribute):
                setattr(self, attribute, value)
        session.add(self)
        if commit:
            session.commit()
        return self

    @classmethod
    def sync_sequence(cls, session: Session, id_column: str = "id") -> None:
        """
        Synchronize the db sequence for the given table's id column.

        Args:
            session: SQLAlchemy session object
            id_column: The name of the ID column to synchronize (default is "id")
        """
        table_name = cls.__tablename__

        # Step 1: Get the sequence name
        sequence_name_query = text("SELECT pg_get_serial_sequence(:table_name, :id_column)")
        sequence_name = session.execute(
            sequence_name_query, {"table_name": table_name, "id_column": id_column}
        ).scalar()
        if not sequence_name:
            raise ValueError(f"No sequence found for {table_name}.{id_column}")

        # Step 2: Get the maximum ID
        max_id_query = select(func.max(getattr(cls, id_column)))
        max_id = session.execute(max_id_query).scalar() or 0  # Default to 0 if table is empty

        # Step 3: Set the sequence to MAX(id) + 1
        alter_sequence_query = text(f"ALTER SEQUENCE {sequence_name} RESTART WITH :next_id")
        session.execute(alter_sequence_query, {"next_id": max_id + 1})
        session.commit()  # Commit the sequence change
