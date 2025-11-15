"""
Test configuration and fixtures for BagTracker tests.
"""

import asyncio
import os
import uuid
from decimal import Decimal
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, StaticPool

# Set SQLite mode for tests BEFORE importing models
os.environ["DB_DRIVER_ASYNC"] = "sqlite+aiosqlite"

from backend.databases.models import (
    Balance,
    BalanceHistory,
    Base,
    CexAccount,
    Chain,
    Portfolio,
    RPC,
    Token,
    Transaction,
    User,
    Wallet,
    WalletAddress,
)
from backend.managers import (
    BalanceManager,
    PortfolioManager,
    TransactionManager,
    UserManager,
    WalletManager,
)
from backend.schemas import TransactionStatus, TransactionType, WalletType
from backend.security import hash_password
from backend.settings import Settings, get_settings


# Configure pytest-asyncio
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Get test settings."""
    return get_settings()


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Create async engine for tests using in-memory SQLite."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,  # Use StaticPool to ensure same connection is reused
        connect_args={"check_same_thread": False},
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async session for tests."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


# Manager fixtures
@pytest_asyncio.fixture
async def user_manager(async_session: AsyncSession, test_settings: Settings) -> UserManager:
    """User manager instance."""
    return UserManager(async_session, test_settings)


@pytest_asyncio.fixture
async def wallet_manager(async_session: AsyncSession, test_settings: Settings) -> WalletManager:
    """Wallet manager instance."""
    return WalletManager(async_session, test_settings)


@pytest_asyncio.fixture
async def balance_manager(async_session: AsyncSession, test_settings: Settings) -> BalanceManager:
    """Balance manager instance."""
    return BalanceManager(async_session, test_settings)


@pytest_asyncio.fixture
async def transaction_manager(async_session: AsyncSession, test_settings: Settings) -> TransactionManager:
    """Transaction manager instance."""
    return TransactionManager(async_session, test_settings)


@pytest_asyncio.fixture
async def portfolio_manager(async_session: AsyncSession, test_settings: Settings) -> PortfolioManager:
    """Portfolio manager instance."""
    return PortfolioManager(async_session, test_settings)


# Test data fixtures
@pytest_asyncio.fixture
async def test_user(async_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("TestPass123!"),
    )
    await user.save(async_session)
    return user


@pytest_asyncio.fixture
async def test_user_2(async_session: AsyncSession) -> User:
    """Create a second test user."""
    user = User(
        username="testuser2",
        email="test2@example.com",
        password_hash=hash_password("TestPass123!"),
    )
    await user.save(async_session)
    return user


@pytest_asyncio.fixture
async def test_chain(async_session: AsyncSession) -> Chain:
    """Create a test blockchain chain (Ethereum)."""
    chain = Chain(
        chain_id=1,
        name="Ethereum",
        short_name="ETH",
        chain_type="evm",
        explorer_url="https://etherscan.io",
        is_testnet=False,
    )
    await chain.save(async_session)
    return chain


@pytest_asyncio.fixture
async def test_chain_bsc(async_session: AsyncSession) -> Chain:
    """Create a test blockchain chain (BSC)."""
    chain = Chain(
        chain_id=56,
        name="Binance Smart Chain",
        short_name="BSC",
        chain_type="evm",
        explorer_url="https://bscscan.com",
        is_testnet=False,
    )
    await chain.save(async_session)
    return chain


@pytest_asyncio.fixture
async def test_token(async_session: AsyncSession, test_chain: Chain) -> Token:
    """Create a test token (ETH)."""
    token = Token(
        chain_id=test_chain.id,
        contract_address=None,
        contract_address_lowercase=None,
        symbol="ETH",
        name="Ethereum",
        decimals=18,
        is_native=True,
        coingecko_id="ethereum",
        current_price_usd=Decimal("2000.50"),
    )
    await token.save(async_session)
    return token


@pytest_asyncio.fixture
async def test_token_usdt(async_session: AsyncSession, test_chain: Chain) -> Token:
    """Create a test token (USDT)."""
    token = Token(
        chain_id=test_chain.id,
        contract_address="0xdac17f958d2ee523a2206206994597c13d831ec7",
        contract_address_lowercase="0xdac17f958d2ee523a2206206994597c13d831ec7".lower(),
        symbol="USDT",
        name="Tether USD",
        decimals=6,
        is_native=False,
        coingecko_id="tether",
        current_price_usd=Decimal("1.00"),
    )
    await token.save(async_session)
    return token


@pytest_asyncio.fixture
async def test_wallet(async_session: AsyncSession, test_user: User, test_chain: Chain) -> Wallet:
    """Create a test wallet with one address."""
    wallet = Wallet(
        user_id=test_user.id,
        wallet_type=WalletType.METAMASK.value,
        sync_enabled=True,
        total_value_usd=Decimal(0),
    )
    await wallet.save(async_session)

    # Add address
    address = WalletAddress(
        wallet_id=wallet.id,
        chain_id=test_chain.id,
        address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        address_lowercase="0x742d35cc6634c0532925a3b844bc9e7595f0beb",
    )
    await address.save(async_session)

    # Refresh to get relationships
    await async_session.refresh(wallet)
    return wallet


@pytest_asyncio.fixture
async def test_portfolio(async_session: AsyncSession, test_user: User) -> Portfolio:
    """Create a test portfolio."""
    portfolio = Portfolio(
        name="Test Portfolio",
        owner_id=test_user.id,
    )
    await portfolio.save(async_session)
    return portfolio


@pytest_asyncio.fixture
async def test_transaction_buy(
    async_session: AsyncSession, test_wallet: Wallet, test_token: Token, test_chain: Chain
) -> Transaction:
    """Create a test BUY transaction."""
    from datetime import UTC, datetime

    tx = Transaction(
        wallet_id=test_wallet.id,
        token_id=test_token.id,
        chain_id=test_chain.id,
        transaction_type=TransactionType.BUY.value,
        amount=Decimal("1000000000000000000"),  # 1 ETH in wei
        amount_decimal=Decimal("1.0"),
        price_usd=Decimal("2000.50"),
        transaction_hash="0xabc123def456",
        block_number=12345678,
        timestamp=datetime.now(UTC),
        status=TransactionStatus.CONFIRMED.value,
    )
    await tx.save(async_session)
    return tx


@pytest_asyncio.fixture
async def test_balance(
    async_session: AsyncSession, test_wallet: Wallet, test_token: Token, test_chain: Chain
) -> Balance:
    """Create a test balance."""
    balance = Balance(
        wallet_id=test_wallet.id,
        token_id=test_token.id,
        chain_id=test_chain.id,
        amount=Decimal("1000000000000000000"),  # 1 ETH
        amount_decimal=Decimal("1.0"),
        avg_buy_price_usd=Decimal("2000.50"),
        price_usd=Decimal("2000.50"),
        total_bought_decimal=Decimal("1.0"),
        total_sold_decimal=Decimal("0"),
    )
    await balance.save(async_session)
    return balance


@pytest_asyncio.fixture
async def test_rpc(async_session: AsyncSession, test_chain: Chain) -> RPC:
    """Create a test RPC endpoint."""
    rpc = RPC(
        chain_id=test_chain.id,
        url="https://mainnet.infura.io/v3/test-key",
        is_active=True,
        priority=1,
    )
    await rpc.save(async_session)
    return rpc


@pytest_asyncio.fixture
async def test_cex_account(async_session: AsyncSession, test_user: User) -> CexAccount:
    """Create a test CEX account."""
    cex = CexAccount(
        user_id=test_user.id,
        exchange_name="Binance",
        account_name="Main Account",
        api_key="test_api_key",
        api_secret="test_api_secret",
        is_active=True,
    )
    await cex.save(async_session)
    return cex
