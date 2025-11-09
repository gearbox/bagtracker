from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from backend.databases.models import Base


class WalletAddress(Base):
    """
    Many-to-many relationship between wallets and chains.
    Enables multichain wallet support - same wallet can have addresses on multiple chains.

    Examples:
    - Wallet "Main Portfolio" has 0xABC... on Ethereum (chain_id=1)
    - Same wallet has 0xABC... on Polygon (chain_id=137)
    - Same wallet has 0xABC... on Arbitrum (chain_id=42161)
    """

    __tablename__ = "wallet_addresses"

    wallet_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chain_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("chains.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Address info
    address: Mapped[str] = mapped_column(Text, nullable=False)
    address_lowercase: Mapped[str] = mapped_column(Text, nullable=False, index=True)

    # Optional: for HD wallets
    derivation_path: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="BIP44 derivation path, e.g., m/44'/60'/0'/0/0"
    )

    # Sync tracking per chain
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_block: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="Last synced block number for this chain"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true", index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    wallet = relationship("Wallet", back_populates="addresses")
    chain = relationship("Chain", back_populates="wallet_addresses")

    __table_args__ = (
        # One wallet can only have one address per chain
        UniqueConstraint("wallet_id", "chain_id", name="uq_wallet_chain"),
        # Same address can't exist twice on the same chain (but can on different chains)
        UniqueConstraint("address_lowercase", "chain_id", name="uq_address_chain"),
        # Performance indexes
        Index("ix_wallet_addr_wallet_chain", "wallet_id", "chain_id"),
        Index("ix_wallet_addr_chain_active", "chain_id", "is_active"),
    )

    @validates("address_lowercase")
    def validate_address_lowercase(self, key: str, address: str) -> str:
        """Ensure address is lowercase for consistent lookups."""
        return address.lower().strip() if address else address

    @validates("address")
    def validate_address(self, key: str, address: str) -> str:
        """Basic address validation and normalization."""
        if not address:
            raise ValueError("Address cannot be empty")
        return address.strip()


class Wallet(Base):
    __tablename__ = "wallets"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    portfolio_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("portfolios.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)  # optional user-defined name
    wallet_type: Mapped[str] = mapped_column(String(20), nullable=False)  # metamask, ledger, tronlink
    sync_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    is_watched_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_value_usd: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False, default=0)

    # Relationships
    owner = relationship("User", back_populates="wallets")
    addresses: Mapped[list["WalletAddress"]] = relationship(
        "WalletAddress", back_populates="wallet", cascade="all, delete-orphan"
    )
    portfolio = relationship("Portfolio", back_populates="wallets")
    transactions = relationship("Transaction", back_populates="wallet", cascade="all, delete-orphan")
    balances = relationship("Balance", back_populates="wallet", cascade="all, delete-orphan")
    balances_history = relationship("BalanceHistory", back_populates="wallet", cascade="all, delete-orphan")
    nft_balances = relationship("NFTBalance", back_populates="wallet", cascade="all, delete-orphan")
    nft_balances_history = relationship("NFTBalanceHistory", back_populates="wallet", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_wallets_portfolio", "portfolio_id"),)
