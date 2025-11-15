"""Tests for PortfolioManager"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.databases.models import Portfolio, User, Wallet
from backend.errors import DatabaseError
from backend.managers import PortfolioManager


@pytest.mark.asyncio
class TestPortfolioManager:
    """Test PortfolioManager CRUD operations"""

    async def test_get_portfolio_by_uuid(self, portfolio_manager: PortfolioManager, test_portfolio: Portfolio):
        """Test getting portfolio by UUID"""
        portfolio = await portfolio_manager.get(test_portfolio.uuid)

        assert portfolio.id == test_portfolio.id
        assert portfolio.uuid == test_portfolio.uuid
        assert portfolio.name == test_portfolio.name

    async def test_get_portfolio_not_found(self, portfolio_manager: PortfolioManager):
        """Test getting non-existent portfolio raises error"""
        import uuid

        fake_uuid = uuid.uuid4()

        with pytest.raises(DatabaseError) as exc_info:
            await portfolio_manager.get(fake_uuid)

        assert exc_info.value.status_code == 404

    async def test_get_all_by_user(
        self, portfolio_manager: PortfolioManager, test_user: User, test_portfolio: Portfolio
    ):
        """Test getting all portfolios for a user"""
        portfolios = await portfolio_manager.get_all_by_user(test_user.username)

        assert len(portfolios) >= 1
        portfolio_ids = [p.id for p in portfolios]
        assert test_portfolio.id in portfolio_ids

    async def test_add_wallet_to_portfolio(
        self, portfolio_manager: PortfolioManager, test_portfolio: Portfolio, test_wallet: Wallet
    ):
        """Test adding a wallet to a portfolio"""
        await portfolio_manager.add_wallet_to_portfolio(str(test_portfolio.uuid), str(test_wallet.uuid))

        # Refresh portfolio
        portfolio = await portfolio_manager.get(test_portfolio.uuid)

        wallet_ids = [w.id for w in portfolio.wallets]
        assert test_wallet.id in wallet_ids

    async def test_add_wallet_to_portfolio_duplicate(
        self, portfolio_manager: PortfolioManager, test_portfolio: Portfolio, test_wallet: Wallet
    ):
        """Test adding a wallet that's already in portfolio raises error"""
        # Add wallet first time
        await portfolio_manager.add_wallet_to_portfolio(str(test_portfolio.uuid), str(test_wallet.uuid))

        # Try to add again
        with pytest.raises(DatabaseError) as exc_info:
            await portfolio_manager.add_wallet_to_portfolio(str(test_portfolio.uuid), str(test_wallet.uuid))

        assert exc_info.value.status_code == 400

    async def test_remove_wallet_from_portfolio(
        self, portfolio_manager: PortfolioManager, test_portfolio: Portfolio, test_wallet: Wallet
    ):
        """Test removing a wallet from a portfolio"""
        # Add wallet first
        await portfolio_manager.add_wallet_to_portfolio(str(test_portfolio.uuid), str(test_wallet.uuid))

        # Remove wallet
        await portfolio_manager.remove_wallet_from_portfolio(str(test_portfolio.uuid), str(test_wallet.uuid))

        # Refresh portfolio
        portfolio = await portfolio_manager.get(test_portfolio.uuid)

        wallet_ids = [w.id for w in portfolio.wallets]
        assert test_wallet.id not in wallet_ids

    async def test_remove_wallet_not_in_portfolio(
        self,
        portfolio_manager: PortfolioManager,
        test_portfolio: Portfolio,
        test_wallet: Wallet,
        test_user: User,
        test_chain,
    ):
        """Test removing a wallet that's not in portfolio raises error"""
        # Create a new wallet that's not in portfolio
        from backend.databases.models import Wallet, WalletAddress
        from backend.schemas import WalletType

        new_wallet = Wallet(
            user_id=test_user.id,
            wallet_type=WalletType.METAMASK.value,
            sync_enabled=True,
        )
        await new_wallet.save(portfolio_manager.db)

        address = WalletAddress(
            wallet_id=new_wallet.id,
            chain_id=test_chain.id,
            address="0xDifferentAddress123456789",
            address_lowercase="0xdifferentaddress123456789",
        )
        await address.save(portfolio_manager.db)

        # Try to remove wallet that's not in portfolio
        with pytest.raises(DatabaseError) as exc_info:
            await portfolio_manager.remove_wallet_from_portfolio(str(test_portfolio.uuid), str(new_wallet.uuid))

        assert exc_info.value.status_code == 400

    async def test_portfolio_eager_loading(self, portfolio_manager: PortfolioManager, test_portfolio: Portfolio):
        """Test that portfolio eager loads relationships"""
        portfolio = await portfolio_manager.get(test_portfolio.uuid)

        # Should have owner loaded
        assert hasattr(portfolio, "owner")
        assert portfolio.owner is not None

    async def test_delete_portfolio(self, portfolio_manager: PortfolioManager, test_portfolio: Portfolio):
        """Test soft deleting portfolio"""
        await portfolio_manager.delete(test_portfolio.uuid)

        # Portfolio should not be found in normal queries
        with pytest.raises(DatabaseError):
            await portfolio_manager.get(test_portfolio.uuid)

        # But should be found when including deleted
        deleted_portfolio = await Portfolio.get_by_id(
            portfolio_manager.db, test_portfolio.id, include_deleted=True
        )
        assert deleted_portfolio.is_deleted is True
