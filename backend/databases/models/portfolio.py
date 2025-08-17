from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from backend.databases.postgres import Base
import datetime


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)

    wallets = relationship("Wallet", back_populates="owner")


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)
    address = Column(String, index=True, unique=True)
    blockchain = Column(String, default="ethereum")
    user_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="wallets")
    transactions = relationship("Transaction", back_populates="wallet")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id"))
    tx_hash = Column(String, index=True)
    asset_symbol = Column(String)
    amount = Column(Float)
    fee = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))

    wallet = relationship("Wallet", back_populates="transactions")
