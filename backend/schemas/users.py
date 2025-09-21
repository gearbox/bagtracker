from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator

from backend.schemas import Wallet
from backend.validators import is_uuid


class UserBase(BaseModel):
    username: str | None = None
    email: str | None = None
    name: str | None = None
    last_name: str | None = None
    nickname: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserCreateOrUpdate(UserBase):
    
    @field_validator("username", mode="after")
    @classmethod
    def is_not_uuid(cls, v: str):
        if is_uuid(v):
            raise ValueError(f"Username '{v}' cannot be a UUID.")
        return v

    @field_validator("email", mode="before")
    @classmethod
    def convert_to_lower(cls, v: str):
        if isinstance(v, str):
            return v.lower()
        return v

    @field_validator('username', 'name', 'last_name', mode="before")
    @classmethod
    def check_alphanumeric(cls, v: str, info: ValidationInfo) -> str:
        if isinstance(v, str):
            # info.field_name is the name of the field being validated
            is_alphanumeric = v.replace(' ', '').isalnum()
            assert is_alphanumeric, f'{info.field_name} must be alphanumeric'
        return v


class UserPatch(UserCreateOrUpdate):
    pass


class User(UserBase):
    id: UUID
    wallets: list[Wallet] = []
    portfolios: list = []
    cex_accounts: list = []


class UserAll(BaseModel):
    users: list[User] = []