from uuid import UUID
from typing import List

from pydantic import BaseModel

from backend.schemas import Transaction


class WalletBase(BaseModel):
    address: str
    blockchain: str = "ethereum"

class WalletCreate(WalletBase):
    pass

class Wallet(WalletBase):
    id: UUID
    transactions: List[Transaction] = []
    
    class Config:
        from_attributes = True


class WalletAll(BaseModel):
    wallets: List[Wallet] = []
