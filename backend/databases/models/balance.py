from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_mixin, relationship
from sqlalchemy.sql import func

from backend.databases.models import Base


@declarative_mixin
class BalanceBase:
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False)
    contract_address = Column(String(200), nullable=True)  # ERC-20 / native ETH = special value like "0x0"
    chain_id = Column(Integer, ForeignKey("chains.id"), nullable=False, index=True)
    symbol = Column(String(20), nullable=True)
    name = Column(String(100), nullable=True)
    decimals = Column(Integer, nullable=False, default=18)
    amount = Column(Numeric(78, 0), nullable=False, default=0)  # raw token balance, store as integer
    value_usd = Column(Numeric(precision=20, scale=4), nullable=False, default=0)
    avg_value_usd = Column(Numeric(precision=20, scale=4), nullable=False, default=0)  # average purchase price
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
            "value_usd": self.value_usd,
            "avg_value_usd": self.avg_value_usd,
            "type": self.type,
        }


class Balance(Base, BalanceBase):
    __tablename__ = "balances"

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    wallet = relationship("Wallet", back_populates="balances")
    chain = relationship("Chain", backref="balances")

    __table_args__ = (UniqueConstraint("wallet_id", "contract_address", "chain_id", name="uq_wallet_token_chain"),)

    def to_schema(self) -> dict:
        return {
            "id": self.id,
            "memo": self.memo,
            "updated_at": self.updated_at,
            **super().to_schema(),
        }


class BalanceHistory(Base, BalanceBase):
    __tablename__ = "balances_history"

    fetched_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True, primary_key=True
    )

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
    value_usd = Column(Numeric(precision=20, scale=4), nullable=False, default=0)
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
            "value_usd": self.value_usd,
            "image_url": self.image_url,
        }


class NFTBalance(Base, NFTBalanceBase):
    __tablename__ = "nft_balances"

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    wallet = relationship("Wallet", back_populates="nft_balances")

    __table_args__ = (UniqueConstraint("wallet_id", "contract_address", name="uq_nft_wallet_token"),)

    def to_schema(self) -> dict:
        return {
            "id": self.id,
            "memo": self.memo,
            "updated_at": self.updated_at,
            **super().to_schema(),
        }


class NFTBalanceHistory(Base, NFTBalanceBase):
    __tablename__ = "nft_balances_history"

    fetched_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True, primary_key=True
    )

    wallet = relationship("Wallet", back_populates="nft_balances_history")

    def to_schema(self) -> dict:
        return {
            "id": self.id,
            "fetched_at": self.fetched_at,
            **super().to_schema(),
        }


@declarative_mixin
class CexBalanceBase:
    subaccount_id = Column(UUID(as_uuid=True), ForeignKey("cex_subaccounts.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String(20), nullable=True)  # e.g. "USDT", "BTC"
    name = Column(String(100), nullable=True)
    decimals = Column(Integer, nullable=False, default=18)
    amount = Column(Numeric(78, 0), nullable=False, default=0)  # raw token balance, store as integer
    value_usd = Column(Numeric(precision=20, scale=4), nullable=False, default=0)
    avg_value_usd = Column(Numeric(precision=20, scale=4), nullable=False, default=0)  # average purchase price

    def to_schema(self) -> dict:
        return {
            "subaccount_id": self.subaccount_id,
            "symbol": self.symbol,
            "name": self.name,
            "decimals": self.decimals,
            "amount": self.amount,
            "value_usd": self.value_usd,
            "avg_value_usd": self.avg_value_usd,
        }


class CexBalance(Base, CexBalanceBase):
    __tablename__ = "cex_balances"

    # amount = Column(Numeric(38, 18), nullable=False, default=0)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    subaccount = relationship("CexSubAccount", back_populates="balances")

    __table_args__ = (UniqueConstraint("subaccount_id", "symbol", name="uq_cex_balance_subaccount_symbol"),)

    def to_schema(self) -> dict:
        return {
            "id": self.id,
            "memo": self.memo,
            "updated_at": self.updated_at,
            **super().to_schema(),
        }


class CexBalanceHistory(Base, CexBalanceBase):
    __tablename__ = "cex_balances_history"

    # amount = Column(Numeric(38, 18), nullable=False, default=0)

    fetched_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True, primary_key=True
    )

    subaccount = relationship("CexSubAccount", back_populates="balances_history")

    def to_schema(self) -> dict:
        return {
            "id": self.id,
            "memo": self.memo,
            "fetched_at": self.fetched_at,
            **super().to_schema(),
        }
