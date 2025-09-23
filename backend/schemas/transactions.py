import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TxType(StrEnum):
    BUY = "buy"
    SELL = "sell"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"


class TransactionBase(BaseModel):
    tx_hash: str | None = None
    tx_type: TxType
    symbol: str
    amount: Decimal = Decimal('0.00') 
    value_usd: Decimal = Decimal('0.00')
    fee_usd: Decimal = Decimal('0.00')
    timestamp: datetime.datetime

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)

class TransactionCreate(TransactionBase):
    pass

class Transaction(TransactionBase):
    id: UUID
    wallet_id: UUID
    created_at: datetime.datetime
