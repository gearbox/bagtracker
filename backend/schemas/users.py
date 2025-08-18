from pydantic import BaseModel
from typing import List

from backend.schemas import Wallet


class UserBase(BaseModel):
    email: str
    name: str | None = None
    last_name: str | None = None


class UserCreate(UserBase):
    pass


class User(UserBase):
    id: int
    wallets: List[Wallet] = []
    class Config:
        from_attributes = True
