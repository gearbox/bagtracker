from sqlalchemy import or_, select

from backend import schemas
from backend.databases.models import User
from backend.errors import UserError
from backend.managers.base_crud import BaseCRUDManager
from backend.security import hash_password, verify_password
from backend.validators import get_uuid_or_rise


class UserManager(BaseCRUDManager):
    # Define relationships to eager load
    eager_load = [
        "wallets.addresses.chain",
        "portfolios.wallets",
        "cex_accounts",
    ]

    @property
    def _model_class(self) -> type[User]:
        return User

    async def create_user(self, user_data: schemas.UserSignUp) -> User:
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

    async def get_user(self, username_or_uuid: str) -> User:
        try:
            return await self.get_one(uuid=get_uuid_or_rise(username_or_uuid))
        except ValueError:
            return await self.get_one(username=username_or_uuid)

    async def get_user_by_email(self, email: str) -> User:
        if user := await User.get_one(self.db, email=email):
            return user
        raise UserError(status_code=404, exception_message="User not found")

    async def update_user(self, username_or_id: str, user: schemas.UserCreateOrUpdate) -> User:
        if not user.username:
            raise UserError(status_code=400, exception_message="Username field is required")
        user_obj = await self.get_user(username_or_id)
        return await user_obj.update(self.db, update_dict=user.model_dump())

    async def patch_user(self, username_or_id: str, user: schemas.UserPatch) -> User:
        user_obj = await self.get_user(username_or_id)
        return await user_obj.update(self.db, update_dict=user.model_dump(exclude_unset=True))

    async def authenticate_user(self, username_or_email: str, password: str) -> User:
        """
        Authenticate a user by username/email and password.

        Args:
            username_or_email: Username or email address
            password: Plain text password

        Returns:
            User object if authentication successful

        Raises:
            UserError: If user not found or password is incorrect
        """
        # Find user by username or email
        stmt = select(User).filter(
            or_(User.username == username_or_email.lower(), User.email == username_or_email.lower()),
            User.is_deleted == False,  # noqa: E712
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise UserError(status_code=401, exception_message="Invalid username/email or password")

        # Verify password
        if not user.password_hash or not verify_password(password, user.password_hash):
            raise UserError(status_code=401, exception_message="Invalid username/email or password")

        # Update last login time
        from datetime import UTC, datetime

        user.last_login = datetime.now(UTC)
        await user.save(self.db)

        return user

    async def get_or_create_telegram_user(self, telegram_data: schemas.TelegramAuthData) -> tuple[User, bool]:
        """
        Get or create a user from Telegram authentication data.

        Args:
            telegram_data: Telegram user data

        Returns:
            Tuple of (User object, is_new_user boolean)
        """
        # Check if user exists by telegram_id
        stmt = select(User).filter(User.telegram_id == telegram_data.id, User.is_deleted == False)  # noqa: E712
        result = await self.db.execute(stmt)
        if user := result.scalar_one_or_none():
            # Update last login time
            from datetime import UTC, datetime

            user.last_login = datetime.now(UTC)
            # Update telegram_username if changed
            if telegram_data.username and user.telegram_username != telegram_data.username:
                user.telegram_username = telegram_data.username
            await user.save(self.db)
            return user, False

        # Create new user
        # Generate username from telegram data
        username = telegram_data.username or f"tg_{telegram_data.id}"

        # Ensure username is unique
        base_username = username
        counter = 1
        while True:
            stmt = select(User).filter(User.username == username, User.is_deleted == False)  # noqa: E712
            result = await self.db.execute(stmt)
            if not result.scalar_one_or_none():
                break
            username = f"{base_username}_{counter}"
            counter += 1

        new_user = User(
            username=username,
            telegram_id=telegram_data.id,
            telegram_username=telegram_data.username,
            name=telegram_data.first_name,
            last_name=telegram_data.last_name,
            password_hash=None,  # Telegram users don't need password
        )

        from datetime import UTC, datetime

        new_user.last_login = datetime.now(UTC)
        await new_user.save(self.db)

        return new_user, True
