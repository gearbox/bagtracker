from datetime import datetime
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
from sqlalchemy.orm import Mapped, declarative_mixin, mapped_column, relationship
from sqlalchemy.sql import func

from backend.databases.models import Base


class Transaction(Base):
    __tablename__ = "transactions"

    wallet_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("wallets.id", ondelete="CASCADE"), nullable=True, index=True
    )
    cex_account_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("cex_accounts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    chain_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("chains.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    token_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("tokens.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    transaction_hash: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    block_number: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    transaction_index: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Transaction index in block
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)  # pending, confirmed, failed
    counterparty_addr: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g. counterparty address

    # Amount/price
    amount: Mapped[Decimal] = mapped_column(
        Numeric(38, 0),
        nullable=False,
        default=0,
    )  # token balance, store as integer
    price_usd: Mapped[Decimal | None] = mapped_column(Numeric(precision=20, scale=8), nullable=True)

    # Gas/fees
    gas_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gas_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 0), nullable=True)  # Wei for EVM chains
    fee_value: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False, default=0)
    fee_currency: Mapped[str] = mapped_column(String(20), nullable=False, default="USD")

    block_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    token = relationship("Token", back_populates="transactions")
    chain = relationship("Chain", back_populates="transactions")
    wallet = relationship("Wallet", back_populates="transactions")
    cex_account = relationship("CexAccount", back_populates="transactions")

    __table_args__ = (
        CheckConstraint("amount >= 0", name="check_amount_non_negative"),
        CheckConstraint("wallet_id IS NOT NULL OR cex_account_id IS NOT NULL", name="check_has_owner"),
        Index("uq_tx_hash_chain", "transaction_hash", "chain_id", unique=True),
        # Performance indexes
        Index("idx_tx_wallet_time", "wallet_id", "timestamp"),
        Index("idx_tx_chain_status", "chain_id", "status"),
        Index("idx_tx_wallet_token", "wallet_id", "token_id"),
    )


@declarative_mixin
class BalanceBase:
    wallet_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chain_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("chains.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    token_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tokens.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(38, 0), nullable=False, default=0
    )  # raw token balance, store as integer
    amount_decimal: Mapped[Decimal] = mapped_column(
        Numeric(38, 18), nullable=False, default=0
    )  # Human-readable balance
    price_usd: Mapped[Decimal | None] = mapped_column(Numeric(precision=20, scale=8), nullable=True)
    avg_price_usd: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False, default=0
    )  # average purchase price
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
    chain = relationship("Chain", back_populates="balances")

    __table_args__ = (
        UniqueConstraint("wallet_id", "token_id", "chain_id", name="uq_wallet_token_chain"),
        CheckConstraint("amount >= 0", name="non_negative_balance_raw"),
        CheckConstraint("amount_decimal >= 0", name="non_negative_balance_decimal"),
    )

    def to_schema(self, include_id: bool = False) -> dict:
        base_schema = super().to_schema(include_id)
        if self.amount_decimal:
            base_schema["amount_display"] = f"{self.amount_decimal} {self.token.symbol}"
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
    chain = relationship("Chain", back_populates="balances_history")

    __table_args__ = (
        CheckConstraint(
            "snapshot_type IN ('transaction', 'hourly', 'daily', 'weekly', 'monthly')", name="valid_snapshot_type"
        ),
        Index("ix_balance_history_token_date", "token_id", "chain_id", "snapshot_date"),
        Index("ix_balance_history_type_date", "snapshot_type", "snapshot_date"),
        Index("ix_balance_history_wallet_date", "wallet_id", "snapshot_date"),
    )


@declarative_mixin
class NFTBalanceBase:
    wallet_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False)
    contract_address: Mapped[str] = mapped_column(String(200), nullable=False)
    collection_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    symbol: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nft_token_id: Mapped[str] = mapped_column(String(100), nullable=False)
    token_standard: Mapped[str] = mapped_column(String(20), nullable=False, default="ERC721")  # ERC721, ERC1155, etc.
    token_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_metadata: Mapped[str | None] = mapped_column(JSON, nullable=True)  # store JSON metadata
    name: Mapped[str | None] = mapped_column(String(20), nullable=True)
    amount: Mapped[str] = mapped_column(Integer, nullable=False, default=1)  # For ERC1155
    price_usd: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False, default=0)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)


class NFTBalance(Base, NFTBalanceBase):
    __tablename__ = "nft_balances"

    wallet = relationship("Wallet", back_populates="nft_balances")

    __table_args__ = (
        UniqueConstraint("wallet_id", "contract_address", name="uq_nft_wallet_token"),
        CheckConstraint("amount >= 0", name="positive_amount"),
    )


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

    __table_args__ = (Index("idx_nft_history_wallet_date", "wallet_id", "snapshot_date"),)


@declarative_mixin
class CexBalanceBase:
    subaccount_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cex_subaccounts.id", ondelete="CASCADE"), nullable=False
    )
    token_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tokens.id", ondelete="RESTRICT"), nullable=False
    )  # Using native tokens for CEX

    # Balance details
    amount: Mapped[Decimal] = mapped_column(
        Numeric(38, 0), nullable=False, default=0
    )  # raw token balance, store as integer
    amount_decimal: Mapped[Decimal] = mapped_column(
        Numeric(38, 18), nullable=False, default=0
    )  # Human-readable balance
    total_balance: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False, default=0)
    locked_balance: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False, default=0)
    price_usd: Mapped[Decimal | None] = mapped_column(Numeric(precision=20, scale=8), nullable=True)
    # value_usd: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False, default=0)
    avg_price_usd: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False, default=0
    )  # average purchase price
    last_price_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Asset classification
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False, default="spot")  # spot, futures, margin
    is_lending: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_staking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CexBalance(Base, CexBalanceBase):
    __tablename__ = "cex_balances"

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

    def to_schema(self, include_id: bool = False) -> dict:
        base_schema = super().to_schema(include_id)
        if self.amount_decimal:
            base_schema["amount_display"] = f"{self.amount_decimal} {self.token.symbol}"
        return base_schema


class CexBalanceHistory(Base, CexBalanceBase):
    __tablename__ = "cex_balances_history"

    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True, primary_key=True
    )
    snapshot_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="hourly"
    )  # hourly, daily, weekly, monthly
    triggered_by: Mapped[str | None] = mapped_column(String(50), nullable=True)  # transaction, price_change, scheduled

    subaccount = relationship("CexSubAccount", back_populates="cex_balances_history")
    token = relationship("Token", back_populates="cex_balances_history")

    __table_args__ = (
        CheckConstraint(
            "snapshot_type IN ('transaction', 'hourly', 'daily', 'weekly', 'monthly')", name="valid_cex_snapshot_type"
        ),
        Index("idx_cex_history_subaccount_date", "subaccount_id", "snapshot_date"),
        Index("idx_cex_history_token_date", "token_id", "snapshot_date"),
    )
