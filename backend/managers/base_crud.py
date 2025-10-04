import contextlib
import uuid
from abc import ABC, abstractmethod
from typing import Annotated, Generic, TypeVar

import sqlalchemy.exc
from fastapi import Depends
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend import schemas
from backend.databases import get_async_db_session
from backend.databases.models import Base, User
from backend.errors import BadRequestException, DatabaseError
from backend.validators import get_uuid, get_uuid_or_rise

T = TypeVar("T", bound=Base)


class BaseCRUDManager(ABC, Generic[T]):
    def __init__(self, db: Annotated[AsyncSession, Depends(get_async_db_session)]) -> None:
        self.db = db
        self.model = self._model_class
        if not self.model:
            raise NotImplementedError("Subclasses must define a model.")

    @property
    @abstractmethod
    def _model_class(self) -> type[T]:
        pass

    async def _error_if_exists(self, obj_id: str | int) -> None:
        """
        Rises DatabaseError if object exists or BadRequestException if obj_id is not int or UUID

        Args:
            obj_id: object int ID or UUID ID

        Returns:
            None if object does not exists
        """
        try:
            if isinstance(obj_id, int):
                await self.model.get_by_id(self.db, obj_id)
            elif obj_uuid := get_uuid(obj_id):
                await self.model.get_by_uuid(self.db, obj_uuid)
            else:
                raise BadRequestException()
            raise DatabaseError(status_code=400, exception_message="Object already exists")
        except DatabaseError as e:
            if e.status_code == 404:
                return
            raise

    async def get_user_by_name_or_uuid(self, username_or_uuid: str, include_deleted: bool = False) -> User:
        try:
            return await User.get_by_uuid(self.db, get_uuid_or_rise(username_or_uuid), include_deleted)
        except ValueError:
            return await User.get_one(self.db, include_deleted, username=username_or_uuid)

    async def get_all_by_user(self, username_or_uuid: str, include_deleted: bool = False) -> list[T]:
        if user_uuid := get_uuid(username_or_uuid):
            user = await User.get_by_uuid(self.db, user_uuid, include_deleted)
            return await self.model.get_all(self.db, include_deleted, user_id=user.id)
        user = await User.get_one(self.db, include_deleted, username=username_or_uuid)

        stmt = (
            select(User)
            .filter_by(username=username_or_uuid, is_deleted=False)
            .options(selectinload(getattr(User, self.model.__tablename__)))
        )
        result = await self.db.execute(stmt)
        try:
            user = result.scalar_one()
        except sqlalchemy.exc.NoResultFound:
            raise DatabaseError(404, "User not found") from None
        logger.info("Get all by user, getattr method")
        return getattr(user, self.model.__tablename__)

    async def get_all(self, include_deleted: bool = False, **kwargs) -> list[T]:
        return await self.model.get_all(self.db, include_deleted, **kwargs)

    async def get(self, obj_id: int | uuid.UUID | str, include_deleted: bool = False) -> T:
        try:
            if isinstance(obj_id, int):
                return await self.model.get_by_id(self.db, obj_id, include_deleted)
            return await self.model.get_by_uuid(self.db, get_uuid_or_rise(obj_id), include_deleted)
        except ValueError as e:
            raise BadRequestException() from e

    async def create(self, obj_data: schemas.BaseModel, for_username_or_id: str | None = None) -> T:
        create_dict = obj_data.model_dump(exclude_unset=True)
        with contextlib.suppress(KeyError):
            await self._error_if_exists(create_dict["uuid"])
        user_id = None
        if for_username_or_id:
            user = await self.get_user_by_name_or_uuid(for_username_or_id)
            user_id = user.id
            create_dict["user_id"] = user_id
            logger.debug(f"Create object for {for_username_or_id}. Find user {user}")
        new_obj = self.model()
        return await new_obj.create(self.db, create_dict, user_id)

    async def update(self, obj_id: int | uuid.UUID | str, obj_data: schemas.BaseModel) -> T:
        obj = await self.get(obj_id)
        return await obj.update(self.db, obj_data.model_dump())

    async def upsert(self, obj_data: schemas.BaseModel, for_username_or_id: str | None = None) -> T:
        upsert_dict = obj_data.model_dump(exclude_unset=True)
        user_id = None
        if for_username_or_id:
            user = await self.get_user_by_name_or_uuid(for_username_or_id)
            user_id = user.id
            upsert_dict["user_id"] = user_id
        try:
            obj = await self.model.get_by_uuid(self.db, upsert_dict["uuid"])
        except (KeyError, DatabaseError):
            obj = self.model()
        return await obj.upsert(self.db, upsert_dict, user_id)

    async def patch(self, obj_id: int | uuid.UUID | str, obj_data: schemas.BaseModel) -> T:
        obj = await self.get(obj_id)
        return await obj.update(self.db, obj_data.model_dump(exclude_unset=True))

    async def delete(self, obj_uuid: int | uuid.UUID | str) -> None:
        obj = await self.get(obj_uuid)
        await obj.delete(self.db)

    async def sync_sequence(self) -> None:
        """
        Synchronize the db sequence for the table's id column.
        """
        await self.model.sync_sequence(self.db)
