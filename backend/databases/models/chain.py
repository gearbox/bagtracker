from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from backend.databases.models import Base


class Token(Base):
    """
    Tokens
    def to_human_readable(amount: Decimal, decimals: int) -> Decimal:
    return amount / Decimal(10 ** decimals)

    def to_smallest_unit(amount: Decimal, decimals: int) -> Decimal:
        return amount * Decimal(10 ** decimals)
    """

    __tablename__ = "tokens"

    chain_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("chains.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # Token details
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g. ETH, BNB, TRX, STX, USDC
    name: Mapped[str | None] = mapped_column(String(20), nullable=True)  # e.g. Ethereum, USD Coin, etc.
    decimals: Mapped[int] = mapped_column(Integer, nullable=False)  # e.g. 18, 6, etc.
    contract_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    contract_address_lowercase: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_standard: Mapped[str | None] = mapped_column(
        String(10), nullable=True, default="native"
    )  # e.g. native, ERC-20, BEP-20, nft
    is_native: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    # Price tracking
    coingecko_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    coinmarketcap_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_price_usd: Mapped[Decimal | None] = mapped_column(Numeric(precision=20, scale=8), nullable=True)
    market_cap_usd: Mapped[Decimal | None] = mapped_column(Numeric(precision=30, scale=4), nullable=True)
    volume_24h_usd: Mapped[Decimal | None] = mapped_column(Numeric(precision=20, scale=4), nullable=True)
    price_change_24h_percent: Mapped[Decimal | None] = mapped_column(Numeric(precision=8, scale=4), nullable=True)

    # Metadata
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    whitepaper_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    chain = relationship("Chain", back_populates="tokens")
    transactions = relationship("Transaction", back_populates="token", cascade="all, delete-orphan")
    balances = relationship("Balance", back_populates="token", cascade="all, delete-orphan")
    balances_history = relationship("BalanceHistory", back_populates="token", cascade="all, delete-orphan")
    cex_balances = relationship("CexBalance", back_populates="token", cascade="all, delete-orphan")
    cex_balances_history = relationship("CexBalanceHistory", back_populates="token", cascade="all, delete-orphan")

    __table_args__ = (
        # Unique constraint for token identification
        UniqueConstraint("contract_address_lowercase", "chain_id", name="uq_token_contract_chain"),
        UniqueConstraint("symbol", "chain_id", "contract_address_lowercase", name="uq_token_symbol_chain_contract"),
        # Validation constraints
        CheckConstraint("decimals >= 0 AND decimals <= 18", name="safe_decimals_range"),
        CheckConstraint("current_price_usd IS NULL OR current_price_usd >= 0", name="non_negative_price"),
        Index("idx_token_chain_native", "chain_id", "is_native"),
        Index("idx_token_price", "current_price_usd"),
        Index("idx_token_symbol_chain", "symbol", "chain_id"),
    )

    @validates("contract_address_lowercase")
    def validate_contract_address_lowercase(self, key, address):
        return address.lower().strip() if address else address

    @validates("contract_address")
    def validate_contract_address(self, key, address):
        """Basic address validation"""
        return address.strip() if address else address

    @validates("symbol")
    def validate_symbol(self, key, symbol):
        """Ensure symbol is uppercase and valid"""
        return symbol.upper().strip() if symbol else symbol

    def is_native_token(self) -> bool:
        """Check if this is a native blockchain token"""
        return self.is_native or self.contract_address is None

    def get_display_name(self) -> str:
        """Get user-friendly display name"""
        return self.name or self.symbol

    def to_human_readable(self, amount: int | Decimal) -> Decimal:
        """Convert smallest unit to human readable"""
        return Decimal(amount) / Decimal(10**self.decimals)

    def to_smallest_unit(self, amount: Decimal) -> int:
        """Convert human readable to smallest unit"""
        return int(amount * Decimal(10**self.decimals))


class Chain(Base):
    """
    Blockchain networks supported, e.g. Ethereum Mainnet, BSC, Tron, Stacks, Solana, etc.
    Used to link wallets and tokens to specific chains.
    Each chain has a unique numeric chain_id (for EVM chains) or native identifier.

    Chains table example:

    | id | name         | name_full           | chain_type | chain_id  | native_symbol | explorer_url                |
    | -- | ------------ | ------------------- | ---------- | --------- | ------------- | --------------------------- |
    | 1  | eth-mainnet  | Ethereum Mainnet    | evm        | 1         | ETH           | https://etherscan.io/       |
    | 2  | bsc-mainnet  | Binance Smart Chain | evm        | 56        | BNB           | https://bscscan.com/        |
    | 3  | tron-mainnet | Tron Mainnet        | non-evm    | 728126428 | TRX           | https://tronscan.org/       |
    | 4  | stx-mainnet  | Stacks Mainnet      | non-evm    | 5757      | STX           | https://explorer.hiro.so    |
    | 5  | sol-mainnet  | Solana Mainnet      | non-evm    | None      | SOL           | https://explorer.solana.com/|

    """

    __tablename__ = "chains"

    name: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # short identifier, e.g. "eth-mainnet"
    name_full: Mapped[str | None] = mapped_column(Text, nullable=True)  # Human-readable name, e.g. "Ethereum Mainnet"
    chain_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "evm", "bitcoin", "tron", "solana" etc.
    chain_id: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # for EVM - numeric as str, e.g. "1", "56", others: null or native id
    explorer_url: Mapped[str | None] = mapped_column(Text, nullable=True)  # optional: e.g. "https://etherscan.io/"
    block_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Average block time
    is_testnet: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    tokens = relationship("Token", back_populates="chain")
    wallets = relationship("Wallet", back_populates="chain")
    transactions = relationship("Transaction", back_populates="chain")
    balances = relationship("Balance", back_populates="chain")
    balances_history = relationship("BalanceHistory", back_populates="chain")
    rpcs = relationship("RPC", back_populates="chain", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_chain_active_testnet", "is_active", "is_testnet"),)


class RPC(Base):
    """RPC endpoints for chains"""

    __tablename__ = "rpcs"

    chain_id = mapped_column(BigInteger, ForeignKey("chains.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    rpc_url: Mapped[str | None] = mapped_column(Text, nullable=True)  # optional: e.g. "mainnet.infura.io"
    is_failover_url: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # Lower = higher priority
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    chain = relationship("Chain", back_populates="rpcs")

    __table_args__ = (
        UniqueConstraint("chain_id", "name", name="uq_rpc_chain_name"),
        Index("idx_rpc_chain_priority", "chain_id", "priority", "is_active"),
    )
