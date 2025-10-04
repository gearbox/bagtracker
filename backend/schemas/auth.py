from pydantic import BaseModel, Field

from backend.schemas import UserLoginInfo


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, description="Username or email")
    password: str = Field(..., min_length=8, description="User password")


class LoginResponse(BaseModel):
    access_token: str = Field(..., serialization_alias="X-Auth-Token")
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserLoginInfo  # Basic user info


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
