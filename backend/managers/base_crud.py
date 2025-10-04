import contextlib
import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Annotated, Generic, TypeVar

from fastapi import Depends
from loguru import logger

from backend import schemas
from backend.databases import get_db_session
from backend.databases.models import Base, User
from backend.errors import BadRequestException, DatabaseError
from backend.validators import get_uuid, get_uuid_or_rise

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

    def _error_if_exists(self, obj_id: str | int) -> None:
        """
        Rises DatabaseError if object exists or BadRequestException if obj_id is not int or UUID

        Return: None if object does not exists
        """
        try:
            if isinstance(obj_id, int):
                self.model.get_by_id(self.db, obj_id)
            elif obj_uuid := get_uuid(obj_id):
                self.model.get_by_uuid(self.db, obj_uuid)
            else:
                raise BadRequestException()
            raise DatabaseError(status_code=400, exception_message="Object already exists")
        except DatabaseError as e:
            if e.status_code == 404:
                return
            raise

    def get_user_by_name_or_uuid(self, username_or_uuid: str, include_deleted: bool = False) -> User:
        try:
            return User.get_by_uuid(self.db, get_uuid_or_rise(username_or_uuid), include_deleted)
        except ValueError:
            return User.get_one(self.db, include_deleted, username=username_or_uuid)

    def get_all_by_user(self, username_or_uuid: str, include_deleted: bool = False) -> list[T]:
        if user_uuid := get_uuid(username_or_uuid):
            user = User.get_by_uuid(self.db, user_uuid, include_deleted)
            return self.model.get_all(self.db, include_deleted, user_id=user.id)
        user = User.get_one(self.db, include_deleted, username=username_or_uuid)
        logger.info("Get all by user, getattr method")
        return getattr(user, self.model.__tablename__)

    def get_all(self, include_deleted: bool = False, **kwargs) -> list[T]:
        return self.model.get_all(self.db, include_deleted, **kwargs)

    def get(self, obj_id: int | uuid.UUID | str, include_deleted: bool = False) -> T:
        try:
            if isinstance(obj_id, int):
                return self.model.get_by_id(self.db, obj_id, include_deleted)
            return self.model.get_by_uuid(self.db, get_uuid_or_rise(obj_id), include_deleted)
        except ValueError as e:
            raise BadRequestException() from e

    def create(self, obj_data: schemas.BaseModel, for_username_or_id: str | None = None) -> T:
        create_dict = obj_data.model_dump(exclude_unset=True)
        with contextlib.suppress(KeyError):
            self._error_if_exists(create_dict["uuid"])
        user_id = None
        if for_username_or_id:
            user_id = self.get_user_by_name_or_uuid(for_username_or_id).id
            create_dict["user_id"] = user_id
        new_obj = self.model()
        return new_obj.create(self.db, create_dict, user_id)

    def update(self, obj_id: int | uuid.UUID | str, obj_data: schemas.BaseModel) -> T:
        obj = self.get(obj_id)
        return obj.update(self.db, obj_data.model_dump())

    def upsert(self, obj_data: schemas.BaseModel, for_username_or_id: str | None = None) -> T:
        upsert_dict = obj_data.model_dump(exclude_unset=True)
        user_id = None
        if for_username_or_id:
            user_id = self.get_user_by_name_or_uuid(for_username_or_id).id
            upsert_dict["user_id"] = user_id
        obj = None
        with contextlib.suppress(KeyError, DatabaseError):
            if "uuid" in upsert_dict:
                obj = self.model.get_by_uuid(self.db, upsert_dict["uuid"])
        if not obj:
            obj = self.model()
        return obj.upsert(self.db, upsert_dict, user_id)

    def patch(self, obj_id: int | uuid.UUID | str, obj_data: schemas.BaseModel) -> T:
        obj = self.get(obj_id)
        return obj.update(self.db, obj_data.model_dump(exclude_unset=True))

    def delete(self, obj_uuid: int | uuid.UUID | str) -> None:
        self.get(obj_uuid).delete(self.db)

    def sync_sequence(self) -> None:
        """
        Synchronize the db sequence for the table's id column.
        """
        instance = self.model()
        instance.sync_sequence(self.db)
