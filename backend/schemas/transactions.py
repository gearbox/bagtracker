import datetime
from uuid import UUID

from pydantic import BaseModel


class TransactionBase(BaseModel):
    tx_hash: str
    asset_symbol: str
    amount: float
    timestamp: datetime.datetime

class TransactionCreate(TransactionBase):
    pass

class Transaction(TransactionBase):
    id: UUID
    class Config:
        from_attributes = True
