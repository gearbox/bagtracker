from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend import errors
from backend.databases.factory_async import get_async_db_session
from backend.databases.models import User
from backend.security.jwt import decode_access_token
from backend.settings import settings


class TokenAuth(APIKeyHeader):
    """
    Token authentication using a header.
    """

    async def __call__(self, request: Request):
        token = super().__call__(request=request)
        if await token != settings.token:
            raise errors.NotAuthorizedException("Wrong token")


class JWTBearer(HTTPBearer):
    """
    JWT Bearer token authentication.
    Extracts and validates JWT token from Authorization header.
    """

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        credentials = await super().__call__(request)
        if not credentials:
            raise HTTPException(status_code=403, detail="Invalid authorization credentials")

        if credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=403, detail="Invalid authentication scheme")

        try:
            decode_access_token(credentials.credentials)
        except ValueError as e:
            raise HTTPException(status_code=403, detail=str(e)) from e

        return credentials


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(JWTBearer())],
    session: Annotated[AsyncSession, Depends(get_async_db_session)],
) -> User:
    """
    Get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Authorization credentials containing JWT token
        session: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    try:
        token_data = decode_access_token(token)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e

    user = await User.get_one(session, id=token_data.user_id)
    if not user or user.is_deleted:
        raise HTTPException(status_code=404, detail="User not found")

    return user


# Dependencies which are used in all routers based on the project's settings
common = []

token_auth = [
    Depends(TokenAuth(name=settings.token_header_name)),
]

jwt_auth = get_current_user
