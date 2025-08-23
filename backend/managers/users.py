from typing import TYPE_CHECKING

from fastapi import Depends
import sqlalchemy.exc

from backend.databases.postgres import get_db_session
from backend.databases.models import User
from backend import schemas
from backend.errors import DatabaseError, UserError
from backend.validators import get_uuid

if TYPE_CHECKING:
    from sqlalchemy.orm import Session as DBSession


class UserManager:
    def __init__(self, db: "DBSession" = Depends(get_db_session)) -> None:
        self.db = db

    def create_user(self, user: schemas.UserCreateOrUpdate) -> User:
        # TODO: check if we can remove the username presence from router and replace it with validator in schema
        if not user.username:
            raise UserError(status_code=400, exception_message="Username field is required")
        new_user = User(**user.model_dump())
        existing_user = self.db.query(User).filter(User.username == new_user.username).first()
        if existing_user:
            raise UserError(status_code=400, exception_message="This username is already taken")
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

    def get_user(self, username_or_id: str) -> User:
        existing_user = None
        if user_id := get_uuid(username_or_id):
            existing_user = User.get(self.db, user_id)
        else:
            existing_user = User.get_by_kwargs(self.db, username=username_or_id)
        if not existing_user:
            raise UserError(status_code=404, exception_message="User not found")
        return existing_user

    def get_user_by_email(self, email: str) -> User:
        user = User.get_by_kwargs(self.db, email=email)
        if not user:
            raise UserError(status_code=404, exception_message="User not found")
        return user

    def get_all_users(self) -> list[User]:
        return User.get_all(self.db)

    def update_user(self, username_or_id: str, user: schemas.UserCreateOrUpdate) -> User:
        if not user.username:
            raise UserError(status_code=400, exception_message="Username field is required")
        return self.get_user(username_or_id).update(self.db, update_dict=user.model_dump())
    
    def patch_user(self, username_or_id: str, user: schemas.UserCreateOrUpdate) -> User:
        return self.get_user(username_or_id).update(self.db, update_dict=user.model_dump(exclude_unset=True))

    def delete_user(self, username_or_id: str) -> None:
        self.get_user(username_or_id).delete(self.db)
