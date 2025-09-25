import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.databases.models import Base


class User(Base):
    __tablename__ = "users"

    username = Column(String(50), nullable=False, unique=True, index=True)
    password = Column(Text, nullable=True)
    email = Column(Text, nullable=True)
    name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    nickname = Column(String(50), nullable=True)

    wallets = relationship("Wallet", back_populates="owner", cascade="all, delete-orphan")
    portfolios = relationship("Portfolio", back_populates="owner", cascade="all, delete-orphan")
    cex_accounts = relationship("CexAccount", back_populates="owner", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("email", name="users_email_key"),)

    def to_schema(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "name": self.name,
            "last_name": self.last_name,
            "nickname": self.nickname,
            "memo": self.memo,
            "wallets": [wallet.to_schema() for wallet in self.wallets],
            "portfolios": [portfolio.to_schema() for portfolio in self.portfolios],
        }


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

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)  # short identifier, e.g. "eth-mainnet", "bsc-mainnet", etc
    name_full = Column(Text, nullable=True)  # Human-readable name: "Ethereum Mainnet", "Binance Smart Chain"
    chain_type = Column(String(50), nullable=False)  # "evm", "bitcoin", "tron", "stacks", "solana" etc.
    chain_id = Column(Integer, nullable=True)  # EVM: numeric (as str, e.g. "1", "56", "137"), others: null or native id
    native_symbol = Column(String(10), nullable=False)  # e.g. ETH, BNB, TRX, STX
    explorer_url = Column(Text, nullable=True)  # optional: e.g. "https://etherscan.io/"

    def to_schema(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "name_full": self.name_full,
            "chain_type": self.chain_type,
            "chain_id": self.chain_id,
            "native_symbol": self.native_symbol,
            "explorer_url": self.explorer_url,
            "memo": self.memo,
        }


class Portfolio(Base):
    __tablename__ = "portfolios"

    name = Column(String(100), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="portfolios")
    wallets = relationship("Wallet", back_populates="portfolio", cascade="all, delete-orphan")
    cex_accounts = relationship("CexAccount", back_populates="portfolio", cascade="all, delete-orphan")

    def to_schema(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "memo": self.memo,
            "created_at": self.created_at,
            "wallets": [wallet.to_schema() for wallet in self.wallets],
            "cex_accounts": [account.to_schema() for account in self.cex_accounts],
        }


class Wallet(Base):
    __tablename__ = "wallets"

    name = Column(String(100), nullable=True)  # optional user-defined name
    type = Column(String(20), nullable=False)  # metamask, ledger, tronlink
    address = Column(String(100), nullable=False, index=True, unique=True)
    chain_id = Column(Integer, ForeignKey("chains.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="wallets")
    chain = relationship("Chain", backref="wallets")
    portfolio = relationship("Portfolio", back_populates="wallets")
    transactions = relationship("Transaction", back_populates="wallet", cascade="all, delete-orphan")
    balances = relationship("Balance", back_populates="wallet", cascade="all, delete-orphan")
    balances_history = relationship("BalanceHistory", back_populates="wallet", cascade="all, delete-orphan")
    nft_balances = relationship("NFTBalance", back_populates="wallet", cascade="all, delete-orphan")
    nft_balances_history = relationship("NFTBalanceHistory", back_populates="wallet", cascade="all, delete-orphan")

    def to_schema(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "memo": self.memo,
            "created_at": self.created_at,
            "type": self.type,
            "address": self.address,
            "chain": self.chain.to_schema() if self.chain else None,
            "balances": [balance.to_schema() for balance in self.balances],
            "nft_balances": [nft.to_schema() for nft in self.nft_balances],
            "transactions": [tx.to_schema() for tx in self.transactions],
        }


class Transaction(Base):
    __tablename__ = "transactions"

    wallet_id = Column(UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="CASCADE"), nullable=True)
    cex_account_id = Column(UUID(as_uuid=True), ForeignKey("cex_accounts.id", ondelete="CASCADE"), nullable=True)
    tx_hash = Column(String(100), nullable=True)
    tx_type = Column(String(20), nullable=False)
    counterparty_addr = Column(String(100), nullable=True)  # optional, e.g. counterparty address
    symbol = Column(String(20), nullable=False)
    amount = Column(Numeric(78, 0), nullable=False, default=0)  # raw token balance, store as integer
    value_usd = Column(Numeric(precision=20, scale=4), nullable=False, default=0)
    fee_value = Column(Numeric(precision=20, scale=4), nullable=False, default=0)
    fee_currency = Column(String(20), nullable=False, default="USD")
    timestamp = Column(DateTime, default=datetime.datetime.now(datetime.UTC), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    wallet = relationship("Wallet", back_populates="transactions")
    cex_account = relationship("CexAccount", back_populates="transactions")

    def to_schema(self) -> dict:
        return {
            "id": self.id,
            "wallet_id": self.wallet_id,
            "tx_hash": self.tx_hash,
            "tx_type": self.tx_type,
            "counterparty_addr": self.counterparty_addr,
            "symbol": self.symbol,
            "amount": self.amount,
            "value_usd": self.value_usd,
            "fee_value": self.fee_value,
            "fee_currency": self.fee_currency,
            "memo": self.memo,
            "timestamp": self.timestamp,
            "created_at": self.created_at,
        }


class Exchange(Base):
    """Centralized exchanges supported, e.g. Bybit, Binance, BingX, HTX, etc."""

    __tablename__ = "exchanges"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)  # e.g. "bybit"
    display_name = Column(String(100), nullable=True)  # e.g. "Bybit"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    accounts = relationship("CexAccount", back_populates="exchange", cascade="all, delete-orphan")


class CexAccount(Base):
    __tablename__ = "cex_accounts"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    exchange_id = Column(Integer, ForeignKey("exchanges.id"), nullable=False)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=True)

    # For API keys, etc
    api_key = Column(String(255), nullable=True)
    api_secret = Column(String(255), nullable=True)
    passphrase = Column(String(255), nullable=True)  # e.g. for HTX

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="cex_accounts")
    exchange = relationship("Exchange", back_populates="accounts")
    subaccounts = relationship("CexSubAccount", back_populates="account", cascade="all, delete-orphan")
    portfolio = relationship("Portfolio", back_populates="cex_accounts")
    transactions = relationship("Transaction", back_populates="cex_account", cascade="all, delete-orphan")


class CexSubAccount(Base):
    __tablename__ = "cex_subaccounts"

    account_id = Column(UUID(as_uuid=True), ForeignKey("cex_accounts.id"), nullable=False)
    type = Column(String(50), nullable=False)  # e.g. "spot", "funding", "earn", "futures"

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    account = relationship("CexAccount", back_populates="subaccounts")
    balances = relationship("CexBalance", back_populates="subaccount", cascade="all, delete-orphan")
    balances_history = relationship("CexBalanceHistory", back_populates="subaccount", cascade="all, delete-orphan")
