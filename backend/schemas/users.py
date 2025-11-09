from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator, model_validator

from backend.errors import UserError
from backend.schemas import Portfolio, WalletResponse
from backend.validators import is_uuid


class UserBase(BaseModel):
    username: str | None = None
    email: str | None = None
    name: str | None = None
    last_name: str | None = None
    nickname: str | None = None
    memo: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserSignUp(BaseModel):
    username: str
    password: str
    email: str
    name: str | None = None
    last_name: str | None = None
    nickname: str | None = None
    memo: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("username", mode="after")
    @classmethod
    def is_not_uuid(cls, v: str):
        if is_uuid(v):
            raise ValueError(f"Username '{v}' cannot be a UUID.")
        return v

    @field_validator("email", mode="before")
    @classmethod
    def convert_to_lower(cls, v: str):
        return v.lower() if isinstance(v, str) else v

    @field_validator("username", "name", "last_name", mode="before")
    @classmethod
    def check_alphanumeric(cls, v: str, info: ValidationInfo) -> str:
        if isinstance(v, str):
            # info.field_name is the name of the field being validated
            is_alphanumeric = v.replace(" ", "").isalnum()
            assert is_alphanumeric, f"{info.field_name} must be alphanumeric and start with letters"
        return v

    @field_validator("password", mode="after")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserCreateOrUpdate(UserBase):
    @model_validator(mode="after")
    def check_username_provided(self):
        if self.username is None:
            raise UserError(status_code=400, exception_message="Username field is required")
        return self

    @field_validator("username", mode="after")
    @classmethod
    def is_not_uuid(cls, v: str):
        if is_uuid(v):
            raise ValueError(f"Username '{v}' cannot be a UUID.")
        return v

    @field_validator("email", mode="before")
    @classmethod
    def convert_to_lower(cls, v: str):
        return v.lower() if isinstance(v, str) else v

    @field_validator("username", "name", "last_name", mode="before")
    @classmethod
    def check_alphanumeric(cls, v: str, info: ValidationInfo) -> str:
        if isinstance(v, str):
            # info.field_name is the name of the field being validated
            is_alphanumeric = v.replace(" ", "").isalnum()
            assert is_alphanumeric, f"{info.field_name} must be alphanumeric and start with letters"
        return v


class UserPatch(UserBase):
    pass


class UserNew(UserBase):
    uuid: UUID


class User(UserNew):
    wallets: list[WalletResponse] = []
    portfolios: list[Portfolio] = []
    # cex_accounts: list = []


class UserAll(BaseModel):
    users: list[User] = []


class UserMgmt(User):
    id: int
    password_hash: str
    is_deleted: bool
    created_at: datetime | None
    updated_at: datetime | None
    created_by: int | None
    updated_by: int | None


class UserMgmtAll(BaseModel):
    users: Sequence[UserMgmt] = []


class UserLoginInfo(BaseModel):
    uuid: UUID
    username: str
    email: str | None = None
    name: str | None = None
    last_name: str | None = None
    nickname: str | None = None

    model_config = ConfigDict(from_attributes=True)
