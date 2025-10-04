from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
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
    event,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from backend.databases.models import Base
from backend.security.encryption import EncryptedString


class User(Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(String(256), nullable=True)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nickname: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    wallets = relationship("Wallet", back_populates="owner", cascade="all, delete-orphan")
    portfolios = relationship("Portfolio", back_populates="owner", cascade="all, delete-orphan")
    cex_accounts = relationship("CexAccount", back_populates="owner", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("email", name="users_email_key"),
        CheckConstraint(r"email ~ '^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$'", name="check_email_format_lower"),
    )

    @validates("email")
    def validate_email(self, key, email):
        return email.lower().strip() if email else email


class Portfolio(Base):
    __tablename__ = "portfolios"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    total_value_usd: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False, default=0)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner = relationship("User", back_populates="portfolios")
    wallets = relationship("Wallet", back_populates="portfolio", cascade="all, delete-orphan")
    cex_accounts = relationship("CexAccount", back_populates="portfolio", cascade="all, delete-orphan")

    def to_schema(self, include_id: bool = False) -> dict:
        base_schema = super().to_schema(include_id)
        if self.total_value_usd:
            base_schema["total_value_usd_display"] = f"${self.total_value_usd:,.2f}"
        return base_schema


class Wallet(Base):
    __tablename__ = "wallets"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    chain_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("chains.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    portfolio_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("portfolios.id", ondelete="SET NULL"), nullable=True
    )

    name: Mapped[str | None] = mapped_column(String(50), nullable=True)  # optional user-defined name
    wallet_type: Mapped[str] = mapped_column(String(20), nullable=False)  # metamask, ledger, tronlink
    address: Mapped[str] = mapped_column(Text, nullable=False, index=True, unique=True)
    sync_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    is_watched_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_value_usd: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False, default=0)

    owner = relationship("User", back_populates="wallets")
    chain = relationship("Chain", back_populates="wallets")
    portfolio = relationship("Portfolio", back_populates="wallets")
    transactions = relationship("Transaction", back_populates="wallet", cascade="all, delete-orphan")
    balances = relationship("Balance", back_populates="wallet", cascade="all, delete-orphan")
    balances_history = relationship("BalanceHistory", back_populates="wallet", cascade="all, delete-orphan")
    nft_balances = relationship("NFTBalance", back_populates="wallet", cascade="all, delete-orphan")
    nft_balances_history = relationship("NFTBalanceHistory", back_populates="wallet", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("address", "chain_id", name="uq_wallet_address_chain"),
        Index("ix_wallets_user_chain", "user_id", "chain_id"),
        Index("ix_wallets_portfolio", "portfolio_id"),
    )


class Exchange(Base):
    """Centralized exchanges supported, e.g. Bybit, Binance, BingX, HTX, etc."""

    __tablename__ = "exchanges"

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # e.g. "bybit"
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g. "Bybit"
    website_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    rate_limit_per_minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_limit_per_minute: Mapped[int | None] = mapped_column(Integer, nullable=True)

    accounts = relationship("CexAccount", back_populates="exchange", cascade="all, delete-orphan")


class CexAccount(Base):
    __tablename__ = "cex_accounts"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exchange_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("exchanges.id", ondelete="RESTRICT"), nullable=False
    )
    portfolio_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("portfolios.id", ondelete="SET NULL"), nullable=True
    )

    name: Mapped[str | None] = mapped_column(String(50), nullable=True)  # optional user-defined name
    # For API keys, etc
    api_key: Mapped[str | None] = mapped_column(EncryptedString(500), nullable=True)
    api_secret: Mapped[str | None] = mapped_column(EncryptedString(500), nullable=True)
    passphrase: Mapped[str | None] = mapped_column(EncryptedString(500), nullable=True)  # e.g. for HTX
    sync_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_value_usd: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False, default=0)

    owner = relationship("User", back_populates="cex_accounts")
    exchange = relationship("Exchange", back_populates="accounts")
    subaccounts = relationship("CexSubAccount", back_populates="account", cascade="all, delete-orphan")
    portfolio = relationship("Portfolio", back_populates="cex_accounts")
    transactions = relationship("Transaction", back_populates="cex_account", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_cex_account_user_exchange", "user_id", "exchange_id"),)


class CexSubAccount(Base):
    __tablename__ = "cex_subaccounts"

    account_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cex_accounts.id"), nullable=False)

    subaccount_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "spot", "funding", "earn"
    subaccount_name: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Exchange-specific name/ID
    total_value_usd: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False, default=0)

    account = relationship("CexAccount", back_populates="subaccounts")
    cex_balances = relationship("CexBalance", back_populates="subaccount", cascade="all, delete-orphan")
    cex_balances_history = relationship("CexBalanceHistory", back_populates="subaccount", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("account_id", "subaccount_type", "subaccount_name", name="uq_subaccount_identifier"),
    )


# Add event listeners for automatic timestamp updates
@event.listens_for(User, "before_update")
def receive_before_update(mapper, connection, target):
    target.updated_at = datetime.now(UTC)
