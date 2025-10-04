from datetime import UTC, datetime

from backend.errors import UserError
from backend.managers import UserManager
from backend.schemas import LoginRequest, LoginResponse, UserLoginInfo
from backend.security.jwt import create_access_token
from backend.security.password import verify_password
from backend.settings import settings


class AuthManager(UserManager):
    async def login(self, credentials: LoginRequest) -> LoginResponse:
        """
        Authenticate user and return JWT token

        Args:
            credentials: Username/email and password

        Returns:
            LoginResponse with JWT token and user info

        Raises:
            UserError: If credentials are invalid
        """
        user = None

        try:
            if "@" in credentials.username:
                user = await self.get_user_by_email(credentials.username)
            else:
                user = await self.get_user(credentials.username)
        except UserError as e:
            # Don't reveal whether username/email exists
            raise UserError(status_code=401, exception_message="Invalid username or password") from e

        # Verify password
        if not user.password_hash or not verify_password(credentials.password, user.password_hash):
            raise UserError(status_code=401, exception_message="Invalid username or password")

        # Update last login
        user.last_login = datetime.now(UTC)
        await user.save(self.db)

        # Create JWT token
        token_data = {
            "user_id": user.id,
            "username": user.username,
        }
        access_token = create_access_token(token_data)
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes,
            user=UserLoginInfo.model_validate(user),
        )
