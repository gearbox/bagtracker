import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TransactionType(StrEnum):
    BUY = "buy"
    SELL = "sell"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"


class TransactionBase(BaseModel):
    wallet_id: UUID | None = None
    cex_account_id: UUID | None = None
    tx_hash: str | None = None
    tx_type: TransactionType
    counterparty_addr: str | None = None
    symbol: str
    amount: Decimal = Decimal("0.00")
    value_usd: Decimal = Decimal("0.00")
    fee_value: Decimal = Decimal("0.00")
    fee_currency: str = "USD"
    timestamp: datetime.datetime

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)


class TransactionCreateOrUpdate(TransactionBase):
    pass


class TransactionPatch(BaseModel):
    wallet_id: UUID | None = None
    cex_account_id: UUID | None = None
    tx_hash: str | None = None
    tx_type: TransactionType | None = None
    counterparty_addr: str | None = None
    symbol: str | None = None
    amount: Decimal | None = Decimal("0.00")
    value_usd: Decimal | None = Decimal("0.00")
    fee_value: Decimal | None = Decimal("0.00")
    fee_currency: str | None = "USD"
    timestamp: datetime.datetime | None = None

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)


class Transaction(TransactionBase):
    id: UUID
    created_at: datetime.datetime


class TransactionsAll(BaseModel):
    transactions: list[Transaction] = []
