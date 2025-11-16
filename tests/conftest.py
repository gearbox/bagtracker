"""
Test configuration and fixtures.

IMPORTANT: This test suite uses PostgreSQL with TimescaleDB extension.
SQLite is NOT supported due to:
- TimescaleDB hypertables with composite primary keys
- PostgreSQL-specific functions (gen_random_uuid())
- PostgreSQL regex operators
- Partial indexes with WHERE clauses
"""

import asyncio
import os
from datetime import UTC, datetime
from decimal import Decimal
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.databases.models.base import Base
from backend.settings import Settings, get_settings

# Test database URL - use environment variable or default
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql+asyncpg://postgres:Pa55w0rD@localhost:5432/bagtracker_test"
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Get settings for testing."""
    return get_settings()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, pool_pre_ping=True)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

        # Enable TimescaleDB extension and create hypertables
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))

            # Create hypertables for balance history tables
            await conn.execute(
                text("SELECT create_hypertable('balances_history', 'snapshot_date', if_not_exists => TRUE)")
            )
            await conn.execute(
                text("SELECT create_hypertable('nft_balances_history', 'snapshot_date', if_not_exists => TRUE)")
            )
            await conn.execute(
                text("SELECT create_hypertable('cex_balances_history', 'snapshot_date', if_not_exists => TRUE)")
            )
        except Exception as e:
            # If TimescaleDB is not available, continue without it for basic tests
            print(f"Warning: Could not enable TimescaleDB: {e}")

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh database session for each test.

    This fixture provides transaction isolation - each test gets a clean slate.
    """
    async_session_maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_maker() as session:
        yield session
        await session.rollback()  # Rollback any uncommitted changes


@pytest_asyncio.fixture(scope="function")
async def db_session(async_session: AsyncSession) -> AsyncSession:
    """Alias for async_session for compatibility."""
    return async_session


# Factory fixtures for creating test data


@pytest.fixture
def user_factory():
    """Factory for creating test users."""

    def _create_user(**kwargs):
        from backend.databases.models.portfolio import User
        from backend.security import hash_password

        defaults = {
            "username": f"testuser_{os.urandom(4).hex()}",
            "email": f"test_{os.urandom(4).hex()}@example.com",
            "password_hash": hash_password("testpassword123"),
        }
        defaults.update(kwargs)
        return User(**defaults)

    return _create_user


@pytest.fixture
def chain_factory():
    """Factory for creating test chains."""

    def _create_chain(**kwargs):
        from backend.databases.models.chain import Chain

        defaults = {
            "chain_id": int(os.urandom(2).hex(), 16),
            "name": f"Test Chain {os.urandom(4).hex()}",
            "short_name": f"TC{os.urandom(2).hex()}",
            "chain_type": "evm",
            "is_testnet": True,
        }
        defaults.update(kwargs)
        return Chain(**defaults)

    return _create_chain


@pytest.fixture
def token_factory():
    """Factory for creating test tokens."""

    def _create_token(chain_id: int, **kwargs):
        from backend.databases.models.chain import Token

        defaults = {
            "chain_id": chain_id,
            "symbol": f"TST{os.urandom(2).hex().upper()}",
            "name": f"Test Token {os.urandom(4).hex()}",
            "decimals": 18,
            "is_native": False,
        }
        defaults.update(kwargs)

        # Handle contract address
        if not defaults.get("is_native") and not defaults.get("contract_address"):
            contract_addr = f"0x{os.urandom(20).hex()}"
            defaults["contract_address"] = contract_addr
            defaults["contract_address_lowercase"] = contract_addr.lower()

        return Token(**defaults)

    return _create_token


@pytest.fixture
def wallet_factory():
    """Factory for creating test wallets."""

    def _create_wallet(user_id: int, **kwargs):
        from backend.databases.models.wallet import Wallet
        from backend.schemas.wallets import WalletType

        defaults = {
            "user_id": user_id,
            "wallet_type": WalletType.METAMASK,
            "sync_enabled": True,
            "total_value_usd": 0,
        }
        defaults.update(kwargs)
        return Wallet(**defaults)

    return _create_wallet


@pytest.fixture
def wallet_address_factory():
    """Factory for creating test wallet addresses."""

    def _create_wallet_address(wallet_id: int, chain_id: int, **kwargs):
        from backend.databases.models.wallet import WalletAddress

        address = kwargs.pop("address", f"0x{os.urandom(20).hex()}")
        defaults = {
            "wallet_id": wallet_id,
            "chain_id": chain_id,
            "address": address,
            "address_lowercase": address.lower(),
        }
        defaults.update(kwargs)
        return WalletAddress(**defaults)

    return _create_wallet_address


@pytest.fixture
def transaction_factory():
    """Factory for creating test transactions."""

    def _create_transaction(wallet_id: int, token_id: int, chain_id: int, **kwargs):
        from backend.databases.models.balance import Transaction
        from backend.schemas.transactions import TransactionType

        tx_hash = kwargs.pop("transaction_hash", f"0x{os.urandom(32).hex()}")
        defaults = {
            "wallet_id": wallet_id,
            "token_id": token_id,
            "chain_id": chain_id,
            "transaction_type": TransactionType.BUY,
            "amount": Decimal("1000000000000000000"),  # 1 token with 18 decimals
            "amount_decimal": Decimal("1.0"),
            "price_usd": Decimal("100.50"),
            "transaction_hash": tx_hash,
            "timestamp": datetime.now(UTC),
            "block_number": 1000000,
        }
        defaults.update(kwargs)
        return Transaction(**defaults)

    return _create_transaction


@pytest.fixture
def balance_factory():
    """Factory for creating test balances."""

    def _create_balance(wallet_id: int, token_id: int, chain_id: int, **kwargs):
        from backend.databases.models.balance import Balance

        defaults = {
            "wallet_id": wallet_id,
            "token_id": token_id,
            "chain_id": chain_id,
            "amount": Decimal("1000000000000000000"),  # 1 token with 18 decimals
            "amount_decimal": Decimal("1.0"),
            "avg_buy_price_usd": Decimal("100.0"),
            "value_usd": Decimal("100.0"),
        }
        defaults.update(kwargs)
        return Balance(**defaults)

    return _create_balance


@pytest.fixture
def portfolio_factory():
    """Factory for creating test portfolios."""

    def _create_portfolio(user_id: int, **kwargs):
        from backend.databases.models.portfolio import Portfolio

        defaults = {
            "user_id": user_id,
            "name": f"Test Portfolio {os.urandom(4).hex()}",
            "total_value_usd": 0,
        }
        defaults.update(kwargs)
        return Portfolio(**defaults)

    return _create_portfolio
