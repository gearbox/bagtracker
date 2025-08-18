from typing import TYPE_CHECKING

from fastapi import Depends
import sqlalchemy.exc

from backend.databases.postgres import get_db_session
from backend.databases.models import User
from backend import schemas
from backend.errors import DatabaseError, UserError

if TYPE_CHECKING:
    from sqlalchemy.orm import Session as DBSession


class UserManager:
    def __init__(self, db: "DBSession" = Depends(get_db_session)) -> None:
        self.db = db

    def create_user(self, user: schemas.UserCreate) -> User:
        # db_user = User(**user.dict())
        db_user = User(**user.model_dump())
        self._user_save_or_raise(db_user)
        return db_user

    def _user_save_or_raise(self, user: User) -> None:
        try:
            user.save(self.db)
        except sqlalchemy.exc.IntegrityError as e:
            if "Duplicate entry" in str(e):
                pass
            else:
                raise DatabaseError(status_code=500, exception_message="Database integrity error") from e
        except sqlalchemy.exc.SQLAlchemyError as e:
            raise DatabaseError(status_code=500, exception_message="Internal database error") from e
        except Exception as e:
            raise DatabaseError(status_code=500, exception_message="Internal server error") from e

    def get_user(self, user_id: int) -> User:
        user = User.get(self.db, user_id)
        if not user:
            raise UserError(status_code=404, exception_message="User not found")
        return user

    def delete_user(self, user_id: int) -> None:
        user = User.get(self.db, user_id)
        if not user:
            raise UserError(status_code=404, exception_message="User not found")
        user.delete(self.db)
