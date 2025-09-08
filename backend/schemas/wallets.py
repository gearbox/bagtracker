from uuid import UUID
from typing import List
from datetime import datetime

from pydantic import BaseModel

from backend.schemas import Transaction


class WalletBase(BaseModel):
    address: str
    blockchain: str = "ethereum"
    type: str

class WalletCreate(WalletBase):
    pass

class Wallet(WalletBase):
    id: UUID
    address: str
    blockchain: str = "ethereum"
    type: str
    created_at: datetime
    transactions: List[Transaction] = []
    
    class Config:
        from_attributes = True


class WalletAll(BaseModel):
    wallets: List[Wallet] = []
