import uuid

from sqlalchemy import Boolean, Column, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.sql import func, select, text


class Base(DeclarativeBase):
    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    memo = Column(Text, nullable=True)  # optional user-defined memo/description
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="false")

    def save(self, session: Session, commit: bool = True):
        session.add(self)
        if commit:
            session.commit()

    def delete(self, session: Session):
        session.delete(self)
        session.commit()

    @classmethod
    def get(cls, session: Session, item_id: uuid.UUID | int):
        return session.get(cls, item_id)

    @classmethod
    def get_by_kwargs(cls, session: Session, **kwargs):
        return session.query(cls).filter_by(**kwargs).first()
    
    @classmethod
    def get_many_by_kwargs(cls, session: Session, **kwargs):
        return session.query(cls).filter_by(**kwargs).all()

    @classmethod
    def get_all(cls, session: Session) -> list:
        return session.query(cls).all()
    
    @classmethod
    def create(cls, session: Session, create_dict: dict):
        instance = cls(**create_dict)
        session.add(instance)
        session.commit()
        return instance

    def update(self, session: Session, update_dict: dict, commit: bool = True):
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
