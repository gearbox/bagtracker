import uuid

from pydantic import BaseModel
from typing import List

from backend.schemas import Wallet


class UserBase(BaseModel):
    email: str
    name: str | None = None
    last_name: str | None = None
    nickname: str | None = None


class UserCreate(UserBase):
    pass


class User(UserBase):
    id: uuid.UUID
    wallets: List[Wallet] = []
    class Config:
        from_attributes = True


class UserAll(BaseModel):
    users: List[User] = []