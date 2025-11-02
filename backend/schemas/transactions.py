from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TransactionType(StrEnum):
    BUY = "buy"
    SELL = "sell"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"


class TransactionStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TransactionBase(BaseModel):
    chain_id: int | None = None
    token_id: int | None = None

    transaction_hash: str | None = None
    block_number: int | None = None
    transaction_index: int | None = None
    transaction_type: TransactionType = TransactionType.BUY
    status: TransactionStatus = TransactionStatus.CONFIRMED
    counterparty_address: str | None = None
    amount: Decimal = Decimal("0.00")
    price_usd: Decimal = Decimal("0.00")

    gas_used: int | None = 0
    gas_price: Decimal | None = Decimal("0.00")
    fee_value: Decimal = Decimal("0.00")
    fee_currency: str = "USD"

    block_timestamp: datetime | None = datetime.now(UTC)
    detected_at: datetime | None = datetime.now(UTC)
    timestamp: datetime = datetime.now(UTC)

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)


class TransactionCreateOrUpdate(TransactionBase):
    wallet_uuid: UUID | None = None
    cex_account_uuid: UUID | None = None


class TransactionPatch(BaseModel):
    chain_id: int | None = None
    token_id: int | None = None

    transaction_hash: str | None = None
    block_number: int | None = None
    transaction_index: int | None = None
    transaction_type: TransactionType = TransactionType.BUY
    status: TransactionStatus = TransactionStatus.CONFIRMED
    counterparty_address: str | None = None
    amount: Decimal = Decimal("0.00")
    price_usd: Decimal = Decimal("0.00")

    gas_used: int | None = 0
    gas_price: Decimal | None = Decimal("0.00")
    fee_value: Decimal = Decimal("0.00")
    fee_currency: str = "USD"

    block_timestamp: datetime | None = datetime.now(UTC)
    detected_at: datetime | None = datetime.now(UTC)
    timestamp: datetime = datetime.now(UTC)

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)


class Transaction(TransactionBase):
    uuid: UUID
    created_at: datetime


class TransactionsAll(BaseModel):
    transactions: list[Transaction] = []
