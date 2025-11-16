"""
Tests for BalanceManager.

Tests balance management functionality:
- get_wallet_balances()
- get_wallet_balances_by_chain()
- get_wallet_total_value()
- process_transaction()
- recalculate_wallet_balances()
"""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.managers.balance import BalanceManager
from backend.settings import get_settings


@pytest.mark.asyncio
class TestBalanceManagerGetBalances:
    """Test balance retrieval functionality."""

    async def test_get_wallet_balances_empty(self, async_session: AsyncSession, user_factory, wallet_factory):
        """Test get_wallet_balances for wallet with no balances."""
        settings = get_settings()
        manager = BalanceManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        wallet = wallet_factory(user.id)
        await wallet.save(async_session)

        balances = await manager.get_wallet_balances(wallet_id=wallet.id)

        assert len(balances) == 0

    async def test_get_wallet_balances_with_balances(
        self, async_session: AsyncSession, user_factory, wallet_factory, chain_factory, token_factory, balance_factory
    ):
        """Test get_wallet_balances returns balances."""
        settings = get_settings()
        manager = BalanceManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        wallet = wallet_factory(user.id)
        await wallet.save(async_session)

        chain = chain_factory()
        await chain.save(async_session)

        token1 = token_factory(chain.id, symbol="TKN1")
        token2 = token_factory(chain.id, symbol="TKN2")
        await token1.save(async_session)
        await token2.save(async_session)

        balance1 = balance_factory(wallet.id, token1.id, chain.id)
        balance2 = balance_factory(wallet.id, token2.id, chain.id)
        await balance1.save(async_session)
        await balance2.save(async_session)

        balances = await manager.get_wallet_balances(wallet_id=wallet.id)

        assert len(balances) == 2
        token_ids = [b.token_id for b in balances]
        assert token1.id in token_ids
        assert token2.id in token_ids

    async def test_get_wallet_balances_by_uuid(
        self, async_session: AsyncSession, user_factory, wallet_factory, chain_factory, token_factory, balance_factory
    ):
        """Test get_wallet_balances with wallet UUID."""
        settings = get_settings()
        manager = BalanceManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        wallet = wallet_factory(user.id)
        await wallet.save(async_session)

        chain = chain_factory()
        await chain.save(async_session)

        token = token_factory(chain.id)
        await token.save(async_session)

        balance = balance_factory(wallet.id, token.id, chain.id)
        await balance.save(async_session)

        balances = await manager.get_wallet_balances(wallet_uuid=wallet.uuid)

        assert len(balances) == 1
        assert balances[0].wallet_id == wallet.id

    async def test_get_wallet_balances_exclude_zero(
        self, async_session: AsyncSession, user_factory, wallet_factory, chain_factory, token_factory, balance_factory
    ):
        """Test get_wallet_balances excludes zero balances by default."""
        settings = get_settings()
        manager = BalanceManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        wallet = wallet_factory(user.id)
        await wallet.save(async_session)

        chain = chain_factory()
        await chain.save(async_session)

        token1 = token_factory(chain.id, symbol="TKN1")
        token2 = token_factory(chain.id, symbol="TKN2")
        await token1.save(async_session)
        await token2.save(async_session)

        # Positive balance
        balance1 = balance_factory(wallet.id, token1.id, chain.id, amount_decimal=Decimal("1.0"))
        # Zero balance
        balance2 = balance_factory(wallet.id, token2.id, chain.id, amount=0, amount_decimal=Decimal("0.0"))

        await balance1.save(async_session)
        await balance2.save(async_session)

        # Exclude zero (default)
        balances = await manager.get_wallet_balances(wallet_id=wallet.id, include_zero=False)

        assert len(balances) == 1
        assert balances[0].token_id == token1.id

        # Include zero
        balances_with_zero = await manager.get_wallet_balances(wallet_id=wallet.id, include_zero=True)

        assert len(balances_with_zero) == 2

    async def test_get_wallet_balances_by_chain(
        self, async_session: AsyncSession, user_factory, wallet_factory, chain_factory, token_factory, balance_factory
    ):
        """Test get_wallet_balances_by_chain filters by chain."""
        settings = get_settings()
        manager = BalanceManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        wallet = wallet_factory(user.id)
        await wallet.save(async_session)

        chain1 = chain_factory(chain_id=1, name="Ethereum")
        chain2 = chain_factory(chain_id=137, name="Polygon")
        await chain1.save(async_session)
        await chain2.save(async_session)

        token1 = token_factory(chain1.id)
        token2 = token_factory(chain2.id)
        await token1.save(async_session)
        await token2.save(async_session)

        balance1 = balance_factory(wallet.id, token1.id, chain1.id)
        balance2 = balance_factory(wallet.id, token2.id, chain2.id)
        await balance1.save(async_session)
        await balance2.save(async_session)

        # Get balances for chain1 only
        chain1_balances = await manager.get_wallet_balances_by_chain(wallet.id, chain1.id)

        assert len(chain1_balances) == 1
        assert chain1_balances[0].chain_id == chain1.id
        assert chain1_balances[0].token_id == token1.id


@pytest.mark.asyncio
class TestBalanceManagerTotals:
    """Test total value calculations."""

    async def test_get_wallet_total_value_empty(self, async_session: AsyncSession, user_factory, wallet_factory):
        """Test get_wallet_total_value for empty wallet."""
        settings = get_settings()
        manager = BalanceManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        wallet = wallet_factory(user.id)
        await wallet.save(async_session)

        totals = await manager.get_wallet_total_value(wallet.id)

        assert totals["token_count"] == 0

    async def test_get_wallet_total_by_chain_empty(self, async_session: AsyncSession, user_factory, wallet_factory):
        """Test get_wallet_total_by_chain for empty wallet."""
        settings = get_settings()
        manager = BalanceManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        wallet = wallet_factory(user.id)
        await wallet.save(async_session)

        totals_by_chain = await manager.get_wallet_total_by_chain(wallet.id)

        assert len(totals_by_chain) == 0


@pytest.mark.asyncio
class TestBalanceManagerProcessing:
    """Test balance processing and recalculation."""

    async def test_recalculate_wallet_balances_no_transactions(
        self, async_session: AsyncSession, user_factory, wallet_factory
    ):
        """Test recalculate_wallet_balances with no transactions."""
        settings = get_settings()
        manager = BalanceManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        wallet = wallet_factory(user.id)
        await wallet.save(async_session)

        # Recalculate (should handle empty gracefully)
        recalculated = await manager.recalculate_wallet_balances(wallet.id, create_snapshots=False)

        assert len(recalculated) == 0
