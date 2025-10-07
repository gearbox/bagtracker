import contextlib
import uuid
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Annotated, Generic, TypeVar

import sqlalchemy.exc
from fastapi import Depends
from loguru import logger
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, with_loader_criteria

from backend import schemas
from backend.databases import get_async_db_session
from backend.databases.models import Base, User
from backend.errors import BadRequestException, DatabaseError
from backend.validators import get_uuid, get_uuid_or_rise

T = TypeVar("T", bound=Base)


class BaseCRUDManager(ABC, Generic[T]):
    """
    Base CRUD Manager with support for eager loading relationships.

    Subclasses can define eager_load to automatically load relationships.
    """

    # Override in subclasses to specify relationships to eager load
    eager_load: list[str] | None = None

    def __init__(self, db: Annotated[AsyncSession, Depends(get_async_db_session)]) -> None:
        self.db = db
        self.model = self._model_class
        if not self.model:
            raise NotImplementedError("Subclasses must define a model.")

    @property
    @abstractmethod
    def _model_class(self) -> type[T]:
        pass

    def _apply_eager_loading_simple(self, stmt, eager_load: list[str] | None = None):
        """Apply eager loading options to a SQLAlchemy statement."""
        if eager_load := eager_load or self.eager_load:
            for relationship_name in eager_load:
                if hasattr(self.model, relationship_name):
                    stmt = stmt.options(selectinload(getattr(self.model, relationship_name), recursion_depth=3))
                else:
                    logger.warning(f"Relationship '{relationship_name}' not found on model {self.model.__name__}")
        return stmt

    def _apply_eager_loading(
        self, stmt: Select, include_deleted: bool = False, eager_load: list[str] | None = None
    ) -> Select:
        """
        Apply eager loading options to a SQLAlchemy statement.

        Supports nested relationships using dot notation:
        - 'relationship' for single-level
        - 'relationship.nested' for multi-level

        Args:
            stmt: the original SQLAlchemy statement to apply eager loading to
            include_deleted: Whether to include soft-deleted records in relationships
            eager_load: Override default eager loading with custom relationships
        Returns:
            stmt: the SQLAlchemy statement with eager loading
        """
        if eager_load := eager_load or self.eager_load:
            for relationship_path in eager_load:
                # Split by dot to support nested relationships
                parts = relationship_path.split(".")

                # Start with the base model
                current_model = self.model
                if not hasattr(current_model, parts[0]):
                    logger.warning(f"Relationship '{parts[0]}' not found on model {current_model.__name__}")
                    continue

                # Build the chain of selectinload
                rel_attr = getattr(current_model, parts[0])
                loader = selectinload(rel_attr)

                # Apply is_deleted filter using with_loader_criteria
                if not include_deleted:
                    related_model = rel_attr.property.mapper.class_
                    if hasattr(related_model, "is_deleted"):
                        stmt = stmt.options(with_loader_criteria(related_model, related_model.is_deleted == False))  # noqa: E712

                current_model = rel_attr.property.mapper.class_

                # Chain additional levels
                for part in parts[1:]:
                    if not hasattr(current_model, part):
                        logger.warning(f"Relationship '{part}' not found on model {current_model.__name__}")
                        break

                    rel_attr = getattr(current_model, part)
                    loader = loader.selectinload(rel_attr)

                    # Apply is_deleted filter using with_loader_criteria
                    if not include_deleted:
                        related_model = rel_attr.property.mapper.class_
                        if hasattr(related_model, "is_deleted"):
                            stmt = stmt.options(with_loader_criteria(related_model, related_model.is_deleted == False))  # noqa: E712

                    current_model = rel_attr.property.mapper.class_

                stmt = stmt.options(loader)
        return stmt

    def _get_by_kwargs(self, include_deleted: bool = False, **kwargs) -> Select:
        """
        Prepares a SQLAlchemy statement to get an object from DB by keywords args

        Args:
            include_deleted: wether to include items that were soft-deleted
        Returns:
            stmt: the SQLAlchemy statement
        """
        stmt = select(self.model).filter_by(**kwargs)
        if not include_deleted:
            stmt = stmt.filter(self.model.is_deleted == False)  # noqa: E712
        return stmt

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
        """Get User object without eager loading"""
        try:
            return await User.get_one(self.db, include_deleted, uuid=get_uuid_or_rise(username_or_uuid))
        except ValueError:
            return await User.get_one(self.db, include_deleted, username=username_or_uuid)

    async def get_all_by_user(
        self,
        username_or_uuid: str,
        include_deleted: bool = False,
        eager_load: list[str] | None = None,
    ) -> Sequence[T]:
        """Get all objects for a user with optional eager loading."""
        user = await self.get_user_by_name_or_uuid(username_or_uuid, include_deleted)
        return await self.get_all(include_deleted, eager_load, user_id=user.id)

    async def get_all(
        self, include_deleted: bool = False, eager_load: list[str] | None = None, **kwargs
    ) -> Sequence[T]:
        """Get all objects with optional eager loading."""
        stmt = self._get_by_kwargs(include_deleted, **kwargs)
        stmt = self._apply_eager_loading(stmt, include_deleted, eager_load)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_one(self, include_deleted: bool = False, eager_load: list[str] | None = None, **kwargs) -> T:
        try:
            stmt = self._get_by_kwargs(include_deleted, **kwargs)
            stmt = self._apply_eager_loading(stmt, include_deleted, eager_load)
            result = await self.db.execute(stmt)
            return result.scalar_one()
        except sqlalchemy.exc.NoResultFound:
            raise DatabaseError(404, "Object not found") from None
        except ValueError as e:
            raise BadRequestException() from e

    async def get(
        self, obj_id: int | uuid.UUID | str, include_deleted: bool = False, eager_load: list[str] | None = None
    ) -> T:
        """
        Get single object with optional eager loading.

        Args:
            obj_id: Object ID (int, UUID, or string UUID)
            include_deleted: Whether to include soft-deleted records
            eager_load: Override default eager loading with custom relationships
        """
        obj_uuid = get_uuid(obj_id)
        try:
            fiter_by = {"uuid": obj_uuid} if obj_uuid else {"id": int(obj_id)}
        except ValueError as e:
            raise BadRequestException() from e
        else:
            return await self.get_one(include_deleted, eager_load, **fiter_by)

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
        created_obj = await new_obj.create(self.db, create_dict, user_id)

        # Refresh with eager loading
        if self.eager_load:
            await self.db.refresh(created_obj, self.eager_load)
        return created_obj

    async def update(self, obj_id: int | uuid.UUID | str, obj_data: schemas.BaseModel) -> T:
        obj = await self.get(obj_id)
        updated_obj = await obj.update(self.db, obj_data.model_dump())

        # Refresh with eager loading
        if self.eager_load:
            await self.db.refresh(updated_obj, self.eager_load)
        return updated_obj

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
        upserted_obj = await obj.upsert(self.db, upsert_dict, user_id)

        # Refresh with eager loading
        if self.eager_load:
            await self.db.refresh(upserted_obj, self.eager_load)
        return upserted_obj

    async def patch(self, obj_id: int | uuid.UUID | str, obj_data: schemas.BaseModel) -> T:
        obj = await self.get(obj_id)
        patched_obj = await obj.update(self.db, obj_data.model_dump(exclude_unset=True))

        # Refresh with eager loading
        if self.eager_load:
            await self.db.refresh(patched_obj, self.eager_load)
        return patched_obj

    async def delete(self, obj_uuid: int | uuid.UUID | str) -> None:
        obj = await self.get(obj_uuid)
        await obj.delete(self.db)

    async def sync_sequence(self) -> None:
        """
        Synchronize the db sequence for the table's id column.
        """
        await self.model.sync_sequence(self.db)
