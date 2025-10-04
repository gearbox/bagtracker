from sqlalchemy import select

from backend import schemas
from backend.databases.models import User
from backend.errors import UserError
from backend.managers.base_crud import BaseCRUDManager
from backend.security import hash_password
from backend.validators import get_uuid


class UserManager(BaseCRUDManager):
    @property
    def _model_class(self) -> type[User]:
        return User

    async def sign_up(self, user_data: schemas.UserSignUp) -> User:
        """Register a new user with hashed password"""
        # Check if username already exists
        stmt = select(User).filter(User.username == user_data.username, User.is_deleted == False)  # noqa: E712
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            raise UserError(status_code=400, exception_message="This username is already taken")

        # Check if email already exists
        stmt = select(User).filter(User.email == user_data.email, User.is_deleted == False)  # noqa: E712
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            raise UserError(status_code=400, exception_message="This email is already registered")
        # Create user with hashed password
        user_dict = user_data.model_dump(exclude={"password"})
        user_dict["password_hash"] = hash_password(user_data.password)
        new_user = User(**user_dict)
        await new_user.save(self.db)
        return new_user

    async def create_user(self, user: schemas.UserCreateOrUpdate) -> User:
        new_user = User(**user.model_dump())
        stmt = select(User).filter(User.username == new_user.username, User.is_deleted == False)  # noqa: E712
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            raise UserError(status_code=400, exception_message="This username is already taken")
        await new_user.save(self.db)
        return new_user

    # TODO: Do we need thish method? Maybe use `get_user_by_name_or_uuid` instead?
    async def get_user(self, username_or_uuid: str) -> User:
        existing_user = None
        if user_uuid := get_uuid(username_or_uuid):
            existing_user = await self.model.get_by_uuid(self.db, user_uuid)
        else:
            existing_user = await User.get_one(self.db, username=username_or_uuid)
        if not existing_user:
            raise UserError(status_code=404, exception_message="User not found")
        return existing_user

    async def get_user_by_email(self, email: str) -> User:
        if user := await User.get_one(self.db, email=email):
            return user
        raise UserError(status_code=404, exception_message="User not found")

    async def update_user(self, username_or_id: str, user: schemas.UserCreateOrUpdate) -> User:
        if not user.username:
            raise UserError(status_code=400, exception_message="Username field is required")
        user_obj = await self.get_user(username_or_id)
        return await user_obj.update(self.db, update_dict=user.model_dump())

    async def patch_user(self, username_or_id: str, user: schemas.UserCreateOrUpdate) -> User:
        user_obj = await self.get_user(username_or_id)
        return await user_obj.update(self.db, update_dict=user.model_dump(exclude_unset=True))
