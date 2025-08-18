import uuid
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
        new_user = User(**user.model_dump())
        existing_user = self.db.query(User).filter(User.email == new_user.email).first()
        if existing_user:
            raise UserError(status_code=400, exception_message="User with this email already exists")
        self._user_save_or_raise(new_user)
        return new_user

    def _user_save_or_raise(self, user: User) -> None:
        try:
            user.save(self.db)
        except sqlalchemy.exc.IntegrityError as e:
            if "duplicate key value" in str(e):
                pass
            else:
                raise DatabaseError(status_code=500, exception_message=f"Database integrity error: {str(e)}") from e
        except sqlalchemy.exc.SQLAlchemyError as e:
            raise DatabaseError(status_code=500, exception_message=f"Internal database error: {str(e)}") from e
        except Exception as e:
            raise DatabaseError(status_code=500, exception_message=f"Internal server error: {str(e)}") from e

    def get_user(self, user_id: str) -> User:
        user = User.get(self.db, uuid.UUID(user_id))
        if not user:
            raise UserError(status_code=404, exception_message="User not found")
        return user
    
    def get_user_by_email(self, email: str) -> User:
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            raise UserError(status_code=404, exception_message="User not found")
        return user

    def get_all_users(self) -> list[User]:
        return User.get_all(self.db)

    def delete_user(self, user_id: str) -> None:
        user = User.get(self.db, uuid.UUID(user_id))
        if not user:
            raise UserError(status_code=404, exception_message="User not found")
        user.delete(self.db)
