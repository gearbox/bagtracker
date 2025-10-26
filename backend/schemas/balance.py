from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SnapshotType(StrEnum):
    """Types of balance history snapshots."""

    TRANSACTION = "transaction"  # Created on every transaction
    HOURLY = "hourly"  # Scheduled hourly snapshots
    DAILY = "daily"  # Scheduled daily snapshots
    WEEKLY = "weekly"  # Scheduled weekly snapshots
    MONTHLY = "monthly"  # Scheduled monthly snapshots


class BalanceBase(BaseModel):
    """Base balance schema."""

    wallet_id: int
    chain_id: int
    token_id: int
    # TODO: We lack `amount` field, which we have in the db model. Do we need it?
    amount_decimal: Decimal
    avg_price_usd: Decimal
    price_usd: Decimal | None = None
    last_price_update: datetime | None = None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class BalanceResponse(BalanceBase):
    """Balance response for API."""

    uuid: UUID
    created_at: datetime
    updated_at: datetime


class BalanceHistoryPoint(BaseModel):
    """Single history point for charts."""

    snapshot_date: datetime
    snapshot_type: SnapshotType
    amount_decimal: Decimal
    price_usd: Decimal
    triggered_by: str | None = None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class BalanceCalculatedTotals(BaseModel):
    total_value_usd_display: str
    total_value_usd: Decimal | None = None
    total_realized_pnl_usd: Decimal | None
    total_unrealized_pnl_usd: Decimal | None
    total_unrealized_pnl_percent: Decimal | None


class PortfolioHistoryPoint(BalanceCalculatedTotals):
    """
    Aggregated portfolio value at a point in time.
    Used for portfolio charts showing total value over time.
    """

    snapshot_date: datetime
    # total_value_usd: Decimal
    # total_pnl_usd: Decimal | None = None

    model_config = ConfigDict(from_attributes=True)


class WalletBalancesResponse(BalanceCalculatedTotals):
    """Wallet balances summary."""

    wallet_id: int
    balances: list[BalanceResponse]
    token_count: int


class PortfolioChartResponse(BaseModel):
    """Aggregated portfolio history for charts."""

    history: list[PortfolioHistoryPoint]
