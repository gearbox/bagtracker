import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship

from backend.databases.models import Base

class User(Base):
    __tablename__ = "users"

    email = Column(String, unique=True, index=True)
    name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    nickname = Column(String, nullable=True)

    wallets = relationship("Wallet", back_populates="owner")

    def to_schema(self) -> dict:
        data = {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "last_name": self.last_name,
            "nickname": self.nickname,
            "wallets": [wallet.to_schema() for wallet in self.wallets]
        }
        return data


class Wallet(Base):
    __tablename__ = "wallets"

    address = Column(String, index=True, unique=True)
    blockchain = Column(String, default="ethereum")
    user_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="wallets")
    transactions = relationship("Transaction", back_populates="wallet")

    def to_schema(self) -> dict:
        data = {
            "id": self.id,
            "address": self.address,
            "blockchain": self.blockchain,
            "transactions": [tx.to_schema() for tx in self.transactions]
        }
        return data


class Transaction(Base):
    __tablename__ = "transactions"

    wallet_id = Column(Integer, ForeignKey("wallets.id"))
    tx_hash = Column(String, index=True)
    asset_symbol = Column(String)
    amount = Column(Float)
    fee = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))

    wallet = relationship("Wallet", back_populates="transactions")

    def to_schema(self) -> dict:
        data = {
            "id": self.id,
            "wallet_id": self.wallet_id,
            "tx_hash": self.tx_hash,
            "asset_symbol": self.asset_symbol,
            "amount": self.amount,
            "fee": self.fee,
            "timestamp": self.timestamp
        }
        return data
