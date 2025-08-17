from pydantic import BaseModel
import datetime

class TransactionBase(BaseModel):
    tx_hash: str
    asset_symbol: str
    amount: float
    timestamp: datetime.datetime

class TransactionCreate(TransactionBase):
    pass

class Transaction(TransactionBase):
    id: int
    class Config:
        orm_mode = True
