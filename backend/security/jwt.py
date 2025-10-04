from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from pydantic import BaseModel

from backend.settings import settings


class TokenData(BaseModel):
    user_id: int
    username: str
    exp: datetime


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token

    Args:
        data: Payload to encode (should include user_id, username)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> TokenData:
    """
    Decode and validate JWT token

    Args:
        token: JWT token string

    Returns:
        TokenData with user information

    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return TokenData(**payload)
    except JWTError as e:
        raise ValueError("Invalid or expired token") from e


def verify_token(token: str) -> dict[str, Any] | None:
    """
    Verify token and return payload if valid

    Args:
        token: JWT token string

    Returns:
        Decoded payload or None if invalid
    """
    try:
        token_data = decode_access_token(token)
        return {"user_id": token_data.user_id, "username": token_data.username, "exp": token_data.exp}
    except (JWTError, ValueError):
        return None
