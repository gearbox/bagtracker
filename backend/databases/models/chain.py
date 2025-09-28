from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
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

    id: Mapped[int] = mapped_column(primary_key=True)
    chain_id: Mapped[int] = mapped_column(Integer, ForeignKey("chains.id", ondelete="RESTRICT"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g. ETH, BNB, TRX, STX, USDC
    name: Mapped[str | None] = mapped_column(String(20), nullable=True)  # e.g. Ethereum, USD Coin, etc.
    decimals: Mapped[int] = mapped_column(Integer, nullable=False)  # e.g. 18, 6, etc.
    contract_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    contract_address_lowercase: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_standard: Mapped[str | None] = mapped_column(
        String(10), nullable=True, default="native"
    )  # e.g. native, ERC-20, BEP-20, nft
    is_native: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    whitepaper_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    coingecko_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # For price tracking
    coinmarketcap_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    current_price_usd: Mapped[Decimal | None] = mapped_column(Numeric(precision=20, scale=8), nullable=True)
    market_cap_usd: Mapped[Decimal | None] = mapped_column(Numeric(precision=30, scale=4), nullable=True)
    volume_24h_usd: Mapped[Decimal | None] = mapped_column(Numeric(precision=20, scale=4), nullable=True)
    price_change_24h_percent: Mapped[Decimal | None] = mapped_column(Numeric(precision=8, scale=4), nullable=True)

    chains = relationship("Chain", back_populates="token", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="token", cascade="all, delete-orphan")
    balances = relationship("Balance", back_populates="token", cascade="all, delete-orphan")
    balances_hystory = relationship("BalanceHistory", back_populates="token", cascade="all, delete-orphan")
    cex_balances = relationship("CexBalance", back_populates="token", cascade="all, delete-orphan")
    cex_balances_history = relationship("CexBalanceHistory", back_populates="token", cascade="all, delete-orphan")

    __table_args__ = (
        # Unique constraint for token identification
        UniqueConstraint("contract_address_lowercase", "chain_id", name="uq_token_contract_chain"),
        UniqueConstraint("symbol", "chain_id", "contract_address_lowercase", name="uq_token_symbol_chain_contract"),
        # Validation constraints
        CheckConstraint("decimals >= 0 AND decimals <= 77", name="valid_decimals"),
        CheckConstraint("current_price_usd >= 0", name="non_negative_price"),
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
        return self.contract_address is None or self.token_standard == "native"

    def get_display_name(self) -> str:
        """Get user-friendly display name"""
        return self.name or self.symbol


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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # short identifier, e.g. "eth-mainnet"
    name_full: Mapped[str | None] = mapped_column(Text, nullable=True)  # Human-readable name, e.g. "Ethereum Mainnet"
    chain_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "evm", "bitcoin", "tron", "solana" etc.
    # chain_id for EVM - numeric as str, e.g. "1", "56", others: null or native id
    chain_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    explorer_url: Mapped[str | None] = mapped_column(Text, nullable=True)  # optional: e.g. "https://etherscan.io/"
    block_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Average block time
    is_testnet: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    token = relationship("Token", back_populates="chains")

    rpcs = relationship("RPC", back_populates="chain", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="chain", cascade="all, delete-orphan")


class RPC(Base):
    __tablename__ = "rpcs"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    chain_id = mapped_column(Integer, ForeignKey("chains.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    rpc_url: Mapped[str | None] = mapped_column(Text, nullable=True)  # optional: e.g. "mainnet.infura.io"
    is_failover_url: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    chain = relationship("Chain", back_populates="rpcs")
