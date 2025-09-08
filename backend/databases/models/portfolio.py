import datetime

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, Text, ForeignKey, Float, DateTime, Integer, Numeric, JSON, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_mixin
from sqlalchemy.sql import func

from backend.databases.models import Base

class User(Base):
    __tablename__ = "users"

    username = Column(String(50), nullable=False, unique=True, index=True)
    password_hash = Column(Text, nullable=True)
    email = Column(Text, nullable=True)
    name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    nickname = Column(String(50), nullable=True)

    wallets = relationship("Wallet", back_populates="owner")

    __table_args__ = (
        UniqueConstraint("email", name="users_email_key"),
    )

    def to_schema(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "name": self.name,
            "last_name": self.last_name,
            "nickname": self.nickname,
            "wallets": [wallet.to_schema() for wallet in self.wallets],
        }


class Chain(Base):
    # Chains table example:
    # | id | name         | name_full           | chain_type | chain_id  | native_symbol | explorer_url                |
    # | -- | ------------ | ------------------- | ---------- | --------- | ------------- | --------------------------- |
    # | 1  | eth-mainnet  | Ethereum Mainnet    | evm        | 1         | ETH           | https://etherscan.io/       |
    # | 2  | bsc-mainnet  | Binance Smart Chain | evm        | 56        | BNB           | https://bscscan.com/        |
    # | 3  | tron-mainnet | Tron Mainnet        | non-evm    | 728126428 | TRX           | https://tronscan.org/       |
    # | 4  | stx-mainnet  | Stacks Mainnet      | non-evm    | 5757      | STX           | https://explorer.hiro.so |

    __tablename__ = "chains"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)  # short identifier, e.g. "eth-mainnet", "bsc-mainnet", "tron-mainnet"
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
        }


class Wallet(Base):
    __tablename__ = "wallets"

    type = Column(String(20), nullable=False)  # metamask, ledger, tronlink
    address = Column(String(100), nullable=False, index=True, unique=True)
    chain_id = Column(Integer, ForeignKey("chains.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="wallets")
    chain = relationship("Chain", backref="wallets")
    transactions = relationship("Transaction", back_populates="wallet", cascade="all, delete-orphan")
    balances = relationship("Balance", back_populates="wallet", cascade="all, delete-orphan")
    balances_history = relationship("BalanceHistory", back_populates="wallet", cascade="all, delete-orphan")
    nft_balances = relationship("NFTBalance", back_populates="wallet", cascade="all, delete-orphan")
    nft_balances_history = relationship("NFTBalanceHistory", back_populates="wallet", cascade="all, delete-orphan")

    def to_schema(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "address": self.address,
            "chain": self.chain.to_schema() if self.chain else None,
            "transactions": [tx.to_schema() for tx in self.transactions],
        }


class Transaction(Base):
    __tablename__ = "transactions"

    wallet_id = Column(UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="CASCADE"), nullable=True)
    tx_hash = Column(String(100), index=True)
    symbol = Column(String(20))
    amount = Column(Float)
    fee = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))

    wallet = relationship("Wallet", back_populates="transactions")

    def to_schema(self) -> dict:
        return {
            "id": self.id,
            "wallet_id": self.wallet_id,
            "tx_hash": self.tx_hash,
            "symbol": self.symbol,
            "amount": self.amount,
            "fee": self.fee,
            "timestamp": self.timestamp,
        }


@declarative_mixin
class BalanceBase:
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False)
    contract_address = Column(String(200), nullable=True)  # ERC-20 / native ETH = special value like "0x0"
    chain_id = Column(Integer, ForeignKey("chains.id"), nullable=False, index=True)
    symbol = Column(String(20), nullable=True)
    name = Column(String(100), nullable=True)
    decimals = Column(Integer, nullable=False, default=18)
    amount = Column(Numeric(78, 0), nullable=False, default=0)  # raw token balance,store as integer
    usd_value = Column(Numeric(precision=20, scale=4), nullable=True)
    type = Column(String(20), nullable=True)  # native | erc20 | nft

    def to_schema(self) -> dict:
        return {
            "wallet_id": self.wallet_id,
            "contract_address": self.contract_address,
            "chain_id": self.chain_id,
            "symbol": self.symbol,
            "name": self.name,
            "decimals": self.decimals,
            "amount": self.amount,
            "usd_value": self.usd_value,
            "type": self.type,
        }


class Balance(Base, BalanceBase):
    __tablename__ = "balances"

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    wallet = relationship("Wallet", back_populates="balances")
    chain = relationship("Chain", backref="balances")

    __table_args__ = (
        UniqueConstraint("wallet_id", "contract_address", "chain_id", name="uq_wallet_token_chain"),
    )

    def to_schema(self) -> dict:
        return {
            "id": self.id,
            "updated_at": self.updated_at,
            **super().to_schema(),
        }


class BalanceHistory(Base, BalanceBase):
    __tablename__ = "balances_history"

    fetched_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True, primary_key=True)

    wallet = relationship("Wallet", back_populates="balances_history")
    chain = relationship("Chain", backref="balances_history")

    def to_schema(self) -> dict:
        return {
            "id": self.id,
            "fetched_at": self.fetched_at,
            **super().to_schema(),
        }


@declarative_mixin
class NFTBalanceBase:
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False)
    contract_address = Column(String(200), nullable=False)
    collection_name = Column(String(100), nullable=True)
    symbol = Column(String(50), nullable=True)
    token_id = Column(String(100), nullable=False)
    token_url = Column(Text, nullable=True)
    token_metadata = Column(JSON, nullable=True)  # store JSON metadata
    usd_value = Column(Numeric(precision=20, scale=4), nullable=True)
    image_url = Column(Text, nullable=True)

    def to_schema(self) -> dict:
        return {
            "wallet_id": self.wallet_id,
            "contract_address": self.contract_address,
            "collection_name": self.collection_name,
            "symbol": self.symbol,
            "token_id": self.token_id,
            "token_url": self.token_url,
            "token_metadata": self.token_metadata,
            "usd_value": self.usd_value,
            "image_url": self.image_url,
        }


class NFTBalance(Base, NFTBalanceBase):
    __tablename__ = "nft_balances"

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    wallet = relationship("Wallet", back_populates="nft_balances")

    __table_args__ = (
        UniqueConstraint("wallet_id", "contract_address", name="uq_nft_wallet_token"),
    )

    def to_schema(self) -> dict:
        return {
            "id": self.id,
            "updated_at": self.updated_at,
            **super().to_schema(),
        }


class NFTBalanceHistory(Base, NFTBalanceBase):
    __tablename__ = "nft_balances_history"

    fetched_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True, primary_key=True)

    wallet = relationship("Wallet", back_populates="nft_balances_history")

    def to_schema(self) -> dict:
        return {
            "id": self.id,
            "fetched_at": self.fetched_at,
            **super().to_schema(),
        }
