import contextlib
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Annotated, Generic, TypeVar

import sqlalchemy.exc
from fastapi import Depends

from backend import schemas
from backend.databases import get_db_session
from backend.databases.models import Base, User
from backend.errors import DatabaseError, UnexpectedException
from backend.validators import get_uuid, is_uuid

if TYPE_CHECKING:
    from sqlalchemy.orm import Session as DBSession

T = TypeVar("T", bound=Base)


class BaseCRUDManager(ABC, Generic[T]):
    def __init__(self, db: Annotated["DBSession", Depends(get_db_session)]) -> None:
        self.db = db
        self.model = self._model_class
        if not self.model:
            raise NotImplementedError("Subclasses must define a model.")

    @property
    @abstractmethod
    def _model_class(self) -> type[T]:
        pass

    def _save_or_raise(self, obj: Base) -> None:
        try:
            obj.save(self.db)
        except sqlalchemy.exc.IntegrityError as e:
            raise DatabaseError(status_code=500, exception_message=f"Database integrity error: {str(e)}") from e
        except sqlalchemy.exc.SQLAlchemyError as e:
            raise DatabaseError(status_code=500, exception_message=f"Internal database error: {str(e)}") from e
        except Exception as e:
            raise DatabaseError(status_code=500, exception_message=f"Internal server error: {str(e)}") from e

    def _if_user_exists(self, username_or_id: str) -> User:
        if user_id := get_uuid(username_or_id):
            return User.get(self.db, user_id)
        else:
            return User.get_one_by_kwargs(self.db, username=username_or_id)

    def _error_if_exists(self, obj_id: str | int) -> None:
        if self.model.get(self.db, get_uuid(obj_id) or int(obj_id)):
            raise DatabaseError(status_code=400, exception_message="Object already exists")

    def _without_none_values(self, data: dict) -> dict:
        return {k: v for k, v in data.items() if v is not None}

    def create(self, obj_data: schemas.BaseModel, for_username_or_id: str | None = None) -> T:
        create_dict = obj_data.model_dump(exclude_unset=True)
        with contextlib.suppress(KeyError):
            self._error_if_exists(create_dict["id"])
        user_dict = {}
        if for_username_or_id:
            user_dict = {"user_id": self._if_user_exists(for_username_or_id).id}
        new_obj = self.model(**create_dict, **user_dict)
        self._save_or_raise(new_obj)
        return new_obj

    def get_all_by_user(self, username_or_id: str) -> list[T]:
        if is_uuid(username_or_id):
            return self.model.get_many_by_kwargs(self.db, user_id=username_or_id)
        else:
            user = User.get_one_by_kwargs(self.db, username=username_or_id)
            return getattr(user, self.model.__tablename__)

    def get_all_by_kwargs(self, **kwargs) -> list[T]:
        return self.model.get_many_by_kwargs(self.db, **kwargs)

    def get_all(self) -> list[T]:
        return self.model.get_all(self.db)

    def get(self, obj_id: str | int) -> T:
        return self.model.get(self.db, get_uuid(obj_id) or int(obj_id))

    def update(self, obj_id: str | int, obj_data: schemas.BaseModel) -> T:
        obj = self.get(obj_id)
        return obj.update(self.db, obj_data.model_dump())

    def patch(self, obj_id: str | int, obj_data: schemas.BaseModel) -> T:
        obj = self.get(obj_id)
        return obj.update(self.db, obj_data.model_dump(exclude_unset=True))

    def delete(self, obj_id: str) -> None:
        obj = self.get(obj_id)
        try:
            obj.delete(self.db)
        except sqlalchemy.exc.SQLAlchemyError as e:
            raise DatabaseError(exception_message=f"Internal database error: {str(e)}") from e
        except Exception as e:
            raise UnexpectedException(exception_message=f"Internal server error: {str(e)}") from e

    def sync_sequence(self) -> None:
        """
        Synchronize the db sequence for the table's id column.
        """
        instance = self.model()
        instance.sync_sequence(self.db)
