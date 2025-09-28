import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, declarative_mixin, mapped_column, relationship
from sqlalchemy.sql import func

from backend.databases.models import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    uuid: Mapped["uuid.UUID"] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True, server_default=func.gen_random_uuid()
    )

    wallet_id: Mapped["uuid.UUID | None"] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wallets.uuid", ondelete="CASCADE"),
        nullable=True,
    )
    cex_account_id: Mapped["uuid.UUID | None"] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cex_accounts.uuid", ondelete="CASCADE"),
        nullable=True,
    )
    chain_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("chains.id"), nullable=True)
    token_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tokens.id"), nullable=False)

    transaction_hash: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    block_number: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    transaction_index: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Transaction index in block
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="confirmed")  # pending, confirmed, failed
    counterparty_addr: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g. counterparty address
    amount: Mapped[Decimal] = mapped_column(
        Numeric(78, 0),
        nullable=False,
        default=0,
    )  # token balance, store as integer
    value_usd: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False, default=0)
    price_usd: Mapped[Decimal | None] = mapped_column(Numeric(precision=20, scale=8), nullable=True)
    gas_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gas_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 0), nullable=True)  # Wei for EVM chains
    fee_value: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False, default=0)
    fee_currency: Mapped[str] = mapped_column(String(20), nullable=False, default="USD")
    block_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(UTC), server_default=func.now())

    token = relationship("Token", back_populates="transactions")
    chain = relationship("Chain", back_populates="transactions")
    wallet = relationship("Wallet", back_populates="transactions")
    cex_account = relationship("CexAccount", back_populates="transactions")

    __table_args__ = (
        CheckConstraint("amount >= 0", name="check_amount_non_negative"),
        # Business logic uniqueness constraint
        Index("uq_tx_hash_chain", "transaction_hash", "chain_id", unique=True),
        # Performance indexes
        Index("idx_tx_uuid", "uuid"),  # For API lookups
        Index("idx_tx_wallet_time", "wallet_id", "timestamp"),
        # Index("idx_tx_token_time", "token_address", "timestamp"),
    )


@declarative_mixin
class BalanceBase:
    id: Mapped["uuid.UUID"] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    wallet_id: Mapped["uuid.UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False
    )
    chain_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chains.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    token_id: Mapped[int] = mapped_column(Integer, ForeignKey("tokens.id", ondelete="RESTRICT"), nullable=False)

    # contract_address: Mapped[str | None] = mapped_column(
    #     String(200), nullable=True
    # )  # native ETH = special value like "0x0"
    amount: Mapped[Decimal] = mapped_column(
        Numeric(78, 0), nullable=False, default=0
    )  # raw token balance, store as integer
    amount_decimal: Mapped[Decimal] = mapped_column(
        Numeric(38, 18), nullable=False, default=0
    )  # Human-readable balance
    price_usd: Mapped[Decimal | None] = mapped_column(Numeric(precision=20, scale=8), nullable=True)
    value_usd: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False, default=0)
    avg_price_usd: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False, default=0
    )  # average purchase price
    unrealized_pnl_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=4), nullable=True
    )  # Unrealized P&L
    unrealized_pnl_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=8, scale=4), nullable=True
    )  # P&L percentage
    last_price_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Balance(Base, BalanceBase):
    __tablename__ = "balances"

    previous_balance_decimal: Mapped[Decimal | None] = mapped_column(
        Numeric(38, 18), nullable=True
    )  # Previous balance for change tracking
    balance_change_24h: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)  # 24h balance change
    balance_change_percent_24h: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 4), nullable=True
    )  # 24h percentage change

    # Sync tracking
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_sync_block: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Last synced block number
    sync_status: Mapped[str] = mapped_column(String(20), nullable=False, default="synced")  # synced, syncing, error

    # Performance tracking
    all_time_high_usd: Mapped[Decimal | None] = mapped_column(Numeric(precision=20, scale=4), nullable=True)
    all_time_high_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    token = relationship("Token", back_populates="balances")
    wallet = relationship("Wallet", back_populates="balances")
    chain = relationship("Chain", backref="balances")

    __table_args__ = (
        UniqueConstraint("wallet_id", "token_id", "chain_id", name="uq_wallet_token_chain"),
        CheckConstraint("amount >= 0", name="non_negative_balance_raw"),
        CheckConstraint("amount_decimal >= 0", name="non_negative_balance_decimal"),
    )

    def to_schema(self) -> dict:
        base_schema = super().to_schema()
        if self.amount_decimal:
            base_schema["amount_display"] = f"{self.amount_decimal} {self.token.symbol}"
        if self.value_usd:
            base_schema["value_usd_display"] = f"${self.value_usd:,.2f}"
        return base_schema


class BalanceHistory(Base, BalanceBase):
    __tablename__ = "balances_history"

    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True, primary_key=True
    )
    snapshot_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="hourly"
    )  # hourly, daily, weekly, monthly
    triggered_by: Mapped[str | None] = mapped_column(String(50), nullable=True)  # transaction, price_change, scheduled

    token = relationship("Token", back_populates="balances_history")
    wallet = relationship("Wallet", back_populates="balances_history")
    chain = relationship("Chain", backref="balances_history")

    __table_args__ = (
        CheckConstraint(
            "snapshot_type IN ('transaction', 'hourly', 'daily', 'weekly', 'monthly')", name="valid_snapshot_type"
        ),
        Index("ix_balance_history_wallet_date", "wallet_id", "snapshot_date"),
        Index("ix_balance_history_token_date", "token_id", "chain_id", "snapshot_date"),
        Index("ix_balance_history_type_date", "snapshot_type", "snapshot_date"),
        # Partition-friendly index
        Index("ix_balance_history_date_wallet", "snapshot_date", "wallet_id"),
    )


@declarative_mixin
class NFTBalanceBase:
    id: Mapped["uuid.UUID"] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    wallet_id: Mapped["uuid.UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False
    )
    contract_address: Mapped[str] = mapped_column(String(200), nullable=False)
    collection_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    symbol: Mapped[str | None] = mapped_column(String(50), nullable=True)
    token_id: Mapped[str] = mapped_column(String(100), nullable=False)
    token_standard: Mapped[staticmethod] = mapped_column(
        String(20), nullable=False, default="ERC721"
    )  # ERC721, ERC1155, etc.
    amount: Mapped[str] = mapped_column(Integer, nullable=False, default=1)  # For ERC1155
    token_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_metadata: Mapped[str | None] = mapped_column(JSON, nullable=True)  # store JSON metadata
    name: Mapped[str | None] = mapped_column(String(20), nullable=True)
    value_usd: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False, default=0)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)


class NFTBalance(Base, NFTBalanceBase):
    __tablename__ = "nft_balances"

    wallet = relationship("Wallet", back_populates="nft_balances")

    __table_args__ = (
        UniqueConstraint("wallet_id", "contract_address", name="uq_nft_wallet_token"),
        CheckConstraint("amount >= 0", name="positive_amount"),
    )

    def to_schema(self) -> dict:
        base_schema = super().to_schema()
        if self.value_usd:
            base_schema["value_usd_display"] = f"${self.value_usd:,.2f}"
        return base_schema


class NFTBalanceHistory(Base, NFTBalanceBase):
    __tablename__ = "nft_balances_history"

    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True, primary_key=True
    )
    snapshot_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="hourly"
    )  # hourly, daily, weekly, monthly
    triggered_by: Mapped[str | None] = mapped_column(String(50), nullable=True)  # transaction, price_change, scheduled

    wallet = relationship("Wallet", back_populates="nft_balances_history")


@declarative_mixin
class CexBalanceBase:
    id: Mapped["uuid.UUID"] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    subaccount_id: Mapped["uuid.UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cex_subaccounts.id", ondelete="CASCADE"), nullable=False
    )
    token_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tokens.id", ondelete="RESTRICT"), nullable=False
    )  # Using native tokens for CEX

    # Balance details
    amount: Mapped[Decimal] = mapped_column(
        Numeric(78, 0), nullable=False, default=0
    )  # raw token balance, store as integer
    amount_decimal: Mapped[Decimal] = mapped_column(
        Numeric(38, 18), nullable=False, default=0
    )  # Human-readable balance
    total_balance: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False, default=0)
    locked_balance: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False, default=0)
    price_usd: Mapped[Decimal | None] = mapped_column(Numeric(precision=20, scale=8), nullable=True)
    value_usd: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False, default=0)
    avg_price_usd: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False, default=0
    )  # average purchase price
    unrealized_pnl_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=4), nullable=True
    )  # Unrealized P&L
    unrealized_pnl_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=8, scale=4), nullable=True
    )  # P&L percentage
    last_price_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Asset classification
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False, default="spot")  # spot, futures, margin
    is_lending: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_staking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CexBalance(Base, CexBalanceBase):
    __tablename__ = "cex_balances"

    # amount = Column(Numeric(38, 18), nullable=False, default=0)

    previous_balance_decimal: Mapped[Decimal | None] = mapped_column(
        Numeric(38, 18), nullable=True
    )  # Previous balance for change tracking
    balance_change_24h: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)  # 24h balance change
    balance_change_percent_24h: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 4), nullable=True
    )  # 24h percentage change

    # Interest/yield tracking
    total_interest_earned: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True, default=0)
    interest_rate_apy: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)  # Annual percentage yield

    # Sync tracking
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    sync_status: Mapped[str] = mapped_column(String(20), nullable=False, default="synced")  # synced, syncing, error

    # Performance tracking
    all_time_high_usd: Mapped[Decimal | None] = mapped_column(Numeric(precision=20, scale=4), nullable=True)
    all_time_high_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    subaccount = relationship("CexSubAccount", back_populates="cex_balances")
    token = relationship("Token", back_populates="cex_balances")

    __table_args__ = (
        UniqueConstraint("subaccount_id", "token_id", name="uq_cex_balance_subaccount_symbol"),
        CheckConstraint("amount >= 0", name="positive_cex_balance_raw"),
        CheckConstraint("amount_decimal >= 0", name="positive_cex_balance_decimal"),
    )

    def to_schema(self) -> dict:
        base_schema = super().to_schema()
        if self.amount_decimal:
            base_schema["amount_display"] = f"{self.amount_decimal} {self.token.symbol}"
        if self.value_usd:
            base_schema["value_usd_display"] = f"${self.value_usd:,.2f}"
        return base_schema


class CexBalanceHistory(Base, CexBalanceBase):
    __tablename__ = "cex_balances_history"

    # amount = Column(Numeric(38, 18), nullable=False, default=0)

    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True, primary_key=True
    )
    snapshot_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="hourly"
    )  # hourly, daily, weekly, monthly
    triggered_by: Mapped[str | None] = mapped_column(String(50), nullable=True)  # transaction, price_change, scheduled

    subaccount = relationship("CexSubAccount", back_populates="balances_history")
    token = relationship("Token", back_populates="balances_history")
