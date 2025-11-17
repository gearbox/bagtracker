from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as status_code

from backend.databases.models import User
from backend.dependencies import jwt_auth
from backend.managers import AuthManager, UserManager
from backend.schemas import LoginRequest, LoginResponse, TelegramAuthData, TelegramLoginResponse, UserLoginInfo
from backend.security.jwt import create_access_token
from backend.security.telegram import verify_telegram_auth_data

router = APIRouter()


@router.post("/login", response_model=LoginResponse, status_code=status_code.HTTP_200_OK)
async def login(
    login_data: LoginRequest,
    auth_manager: Annotated[AuthManager, Depends(AuthManager)],
) -> LoginResponse:
    """
    Authenticate user with username/email and password.

    Returns JWT access token and user information.
    """
    return LoginResponse.model_validate(await auth_manager.login(login_data))


@router.get("/me", response_model=UserLoginInfo)
async def get_current_user_info(
    current_user: Annotated[User, Depends(jwt_auth)],
) -> UserLoginInfo:
    """
    Get current authenticated user information from JWT token.

    Requires Authorization header with Bearer token.
    """
    return UserLoginInfo.model_validate(current_user)


@router.post("/telegram", response_model=TelegramLoginResponse)
async def telegram_auth(
    telegram_data: TelegramAuthData,
    user_manager: Annotated[UserManager, Depends(UserManager)],
) -> TelegramLoginResponse:
    """
    Authenticate or register user via Telegram Mini App.

    - **id**: Telegram user ID
    - **first_name**: User's first name (optional)
    - **last_name**: User's last name (optional)
    - **username**: Telegram username (optional)
    - **photo_url**: Profile photo URL (optional)
    - **auth_date**: Authentication timestamp
    - **hash**: Authentication hash for verification

    Returns JWT token, user information, and whether this is a new user.

    Note: Set TELEGRAM_BOT_TOKEN environment variable to enable hash verification.
    If not set, verification will be skipped (development mode only).
    """
    # Verify Telegram authentication data
    is_valid = verify_telegram_auth_data(
        telegram_id=telegram_data.id,
        first_name=telegram_data.first_name,
        last_name=telegram_data.last_name,
        username=telegram_data.username,
        photo_url=telegram_data.photo_url,
        auth_date=telegram_data.auth_date,
        hash_value=telegram_data.hash,
    )

    if not is_valid:
        raise HTTPException(status_code=403, detail="Invalid Telegram authentication data")

    # Get or create user
    user, is_new = await user_manager.get_or_create_telegram_user(telegram_data)

    # Create JWT token
    access_token = create_access_token(data={"user_id": user.id, "username": user.username})

    # Return response
    return TelegramLoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserLoginInfo.model_validate(user),
        is_new_user=is_new,
    )
