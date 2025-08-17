from pydantic import BaseModel
from typing import List

from backend.schemas import Transaction


class WalletBase(BaseModel):
    address: str
    blockchain: str = "ethereum"

class WalletCreate(WalletBase):
    pass

class Wallet(WalletBase):
    id: int
    transactions: List[Transaction] = []
    class Config:
        orm_mode = True