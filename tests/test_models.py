"""Tests for database models"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.databases.models import Balance, Chain, Portfolio, Token, Transaction, User, Wallet, WalletAddress
from backend.errors import DatabaseError
from backend.schemas import TransactionStatus, TransactionType, WalletType
from backend.security import hash_password


@pytest.mark.asyncio
class TestBaseModel:
    """Test Base model functionality"""

    async def test_model_save(self, async_session: AsyncSession):
        """Test saving a model"""
        user = User(
            username="savetest",
            email="savetest@example.com",
            password_hash=hash_password("password123"),
        )
        await user.save(async_session)

        assert user.id is not None
        assert user.uuid is not None
        assert user.created_at is not None
        assert user.updated_at is not None

    async def test_model_soft_delete(self, async_session: AsyncSession):
        """Test soft delete functionality"""
        user = User(
            username="deletetest",
            email="deletetest@example.com",
            password_hash=hash_password("password123"),
        )
        await user.save(async_session)

        await user.delete(async_session)

        assert user.is_deleted is True

    async def test_model_restore(self, async_session: AsyncSession):
        """Test restoring a soft-deleted model"""
        user = User(
            username="restoretest",
            email="restoretest@example.com",
            password_hash=hash_password("password123"),
        )
        await user.save(async_session)
        await user.delete(async_session)

        await user.restore(async_session)

        assert user.is_deleted is False

    async def test_model_update(self, async_session: AsyncSession):
        """Test updating a model"""
        user = User(
            username="updatetest",
            email="updatetest@example.com",
            password_hash=hash_password("password123"),
        )
        await user.save(async_session)

        old_updated_at = user.updated_at
        update_dict = {"email": "newemail@example.com"}
        await user.update(async_session, update_dict)

        assert user.email == "newemail@example.com"
        assert user.updated_at > old_updated_at

    async def test_model_get_by_id(self, async_session: AsyncSession):
        """Test getting model by ID"""
        user = User(
            username="gettest",
            email="gettest@example.com",
            password_hash=hash_password("password123"),
        )
        await user.save(async_session)

        retrieved = await User.get_by_id(async_session, user.id)

        assert retrieved.id == user.id
        assert retrieved.username == user.username

    async def test_model_get_by_uuid(self, async_session: AsyncSession):
        """Test getting model by UUID"""
        user = User(
            username="getuuidtest",
            email="getuuidtest@example.com",
            password_hash=hash_password("password123"),
        )
        await user.save(async_session)

        retrieved = await User.get_by_uuid(async_session, user.uuid)

        assert retrieved.uuid == user.uuid
        assert retrieved.username == user.username

    async def test_model_get_one(self, async_session: AsyncSession):
        """Test getting one model by filter"""
        user = User(
            username="getonetest",
            email="getonetest@example.com",
            password_hash=hash_password("password123"),
        )
        await user.save(async_session)

        retrieved = await User.get_one(async_session, username="getonetest")

        assert retrieved.id == user.id

    async def test_model_get_all(self, async_session: AsyncSession):
        """Test getting all models"""
        user1 = User(
            username="getalltest1",
            email="getalltest1@example.com",
            password_hash=hash_password("password123"),
        )
        user2 = User(
            username="getalltest2",
            email="getalltest2@example.com",
            password_hash=hash_password("password123"),
        )
        await user1.save(async_session)
        await user2.save(async_session)

        users = await User.get_all(async_session)

        assert len(users) >= 2
        usernames = [u.username for u in users]
        assert "getalltest1" in usernames
        assert "getalltest2" in usernames

    async def test_model_to_dict(self, async_session: AsyncSession):
        """Test converting model to dict"""
        user = User(
            username="todicttest",
            email="todicttest@example.com",
            password_hash=hash_password("password123"),
        )
        await user.save(async_session)

        user_dict = user.to_dict()

        assert "uuid" in user_dict
        assert "username" in user_dict
        assert "email" in user_dict
        assert "id" not in user_dict  # Internal ID excluded by default

    async def test_model_to_dict_with_id(self, async_session: AsyncSession):
        """Test converting model to dict including ID"""
        user = User(
            username="todictwithidtest",
            email="todictwithidtest@example.com",
            password_hash=hash_password("password123"),
        )
        await user.save(async_session)

        user_dict = user.to_dict(include_id=True)

        assert "id" in user_dict
        assert user_dict["id"] == user.id


@pytest.mark.asyncio
class TestUserModel:
    """Test User model specific functionality"""

    async def test_user_creation(self, async_session: AsyncSession):
        """Test creating a user"""
        user = User(
            username="testuser123",
            email="testuser123@example.com",
            password_hash=hash_password("SecurePass123!"),
        )
        await user.save(async_session)

        assert user.id is not None
        assert user.username == "testuser123"
        assert user.email == "testuser123@example.com"

    async def test_user_relationships(self, async_session: AsyncSession, test_chain: Chain):
        """Test user has relationships to wallets and portfolios"""
        user = User(
            username="reltest",
            email="reltest@example.com",
            password_hash=hash_password("password123"),
        )
        await user.save(async_session)

        wallet = Wallet(user_id=user.id, wallet_type=WalletType.METAMASK.value)
        await wallet.save(async_session)

        portfolio = Portfolio(name="Test Portfolio", owner_id=user.id)
        await portfolio.save(async_session)

        # Refresh to load relationships
        await async_session.refresh(user, ["wallets", "portfolios"])

        assert len(user.wallets) >= 1
        assert len(user.portfolios) >= 1


@pytest.mark.asyncio
class TestWalletModel:
    """Test Wallet model specific functionality"""

    async def test_wallet_creation(self, async_session: AsyncSession, test_user: User):
        """Test creating a wallet"""
        wallet = Wallet(
            user_id=test_user.id,
            wallet_type=WalletType.METAMASK.value,
            sync_enabled=True,
            total_value_usd=Decimal("0"),
        )
        await wallet.save(async_session)

        assert wallet.id is not None
        assert wallet.user_id == test_user.id

    async def test_wallet_with_addresses(self, async_session: AsyncSession, test_user: User, test_chain: Chain):
        """Test wallet with addresses"""
        wallet = Wallet(user_id=test_user.id, wallet_type=WalletType.METAMASK.value)
        await wallet.save(async_session)

        address = WalletAddress(
            wallet_id=wallet.id,
            chain_id=test_chain.id,
            address="0x1234567890123456789012345678901234567890",
            address_lowercase="0x1234567890123456789012345678901234567890".lower(),
        )
        await address.save(async_session)

        # Refresh to load relationships
        await async_session.refresh(wallet, ["addresses"])

        assert len(wallet.addresses) >= 1


@pytest.mark.asyncio
class TestTransactionModel:
    """Test Transaction model specific functionality"""

    async def test_transaction_creation(
        self, async_session: AsyncSession, test_wallet: Wallet, test_token: Token, test_chain: Chain
    ):
        """Test creating a transaction"""
        tx = Transaction(
            wallet_id=test_wallet.id,
            token_id=test_token.id,
            chain_id=test_chain.id,
            transaction_type=TransactionType.BUY.value,
            amount=Decimal("1000000000000000000"),
            amount_decimal=Decimal("1.0"),
            price_usd=Decimal("2000.50"),
            transaction_hash="0xtesthash123",
            timestamp=datetime.now(UTC),
            status=TransactionStatus.CONFIRMED.value,
        )
        await tx.save(async_session)

        assert tx.id is not None
        assert tx.transaction_type == TransactionType.BUY.value


@pytest.mark.asyncio
class TestBalanceModel:
    """Test Balance model specific functionality"""

    async def test_balance_creation(
        self, async_session: AsyncSession, test_wallet: Wallet, test_token: Token, test_chain: Chain
    ):
        """Test creating a balance"""
        balance = Balance(
            wallet_id=test_wallet.id,
            token_id=test_token.id,
            chain_id=test_chain.id,
            amount=Decimal("2000000000000000000"),
            amount_decimal=Decimal("2.0"),
            avg_buy_price_usd=Decimal("2000.00"),
            price_usd=Decimal("2100.00"),
            total_bought_decimal=Decimal("2.0"),
            total_sold_decimal=Decimal("0"),
        )
        await balance.save(async_session)

        assert balance.id is not None
        assert balance.amount_decimal == Decimal("2.0")


@pytest.mark.asyncio
class TestChainModel:
    """Test Chain model specific functionality"""

    async def test_chain_creation(self, async_session: AsyncSession):
        """Test creating a chain"""
        chain = Chain(
            chain_id=137,
            name="Polygon",
            short_name="MATIC",
            chain_type="evm",
            explorer_url="https://polygonscan.com",
            is_testnet=False,
        )
        await chain.save(async_session)

        assert chain.id is not None
        assert chain.chain_id == 137


@pytest.mark.asyncio
class TestTokenModel:
    """Test Token model specific functionality"""

    async def test_token_creation(self, async_session: AsyncSession, test_chain: Chain):
        """Test creating a token"""
        token = Token(
            chain_id=test_chain.id,
            symbol="USDC",
            name="USD Coin",
            decimals=6,
            is_native=False,
            contract_address="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
            contract_address_lowercase="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48".lower(),
            current_price_usd=Decimal("1.00"),
        )
        await token.save(async_session)

        assert token.id is not None
        assert token.symbol == "USDC"
