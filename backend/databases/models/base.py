from sqlalchemy import BIGINT
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    __abstract__ = True

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, index=True, autoincrement=True)

    def save(self, session: Session, commit: bool = True):
        session.add(self)
        if commit:
            session.commit()

    def delete(self, session: Session):
        session.delete(self)
        session.commit()

    @classmethod
    def get(cls, session: Session, item_id: int):
        return session.get(cls, item_id)
    
    def update(self, session: Session, update_dict: dict, commit: bool = True):
        for attribute, value in update_dict.items():
            if hasattr(self, attribute):
                setattr(self, attribute, value)
        session.add(self)
        if commit:
            session.commit()
