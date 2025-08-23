import uuid

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    def save(self, session: Session, commit: bool = True):
        session.add(self)
        if commit:
            session.commit()

    def delete(self, session: Session):
        session.delete(self)
        session.commit()

    @classmethod
    def get(cls, session: Session, item_id: uuid.UUID):
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

    def update(self, session: Session, update_dict: dict, commit: bool = True):
        for attribute, value in update_dict.items():
            if hasattr(self, attribute):
                setattr(self, attribute, value)
        session.add(self)
        if commit:
            session.commit()
        return self
