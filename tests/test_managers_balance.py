"""Tests for BalanceManager"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.databases.models import Balance, Chain, Token, Transaction, Wallet
from backend.managers import BalanceManager
from backend.schemas import TransactionStatus, TransactionType


@pytest.mark.asyncio
class TestBalanceManager:
    """Test BalanceManager CRUD operations"""

    async def test_get_wallet_balances(
        self, balance_manager: BalanceManager, test_wallet: Wallet, test_balance: Balance
    ):
        """Test getting all balances for a wallet"""
        balances = await balance_manager.get_wallet_balances(wallet_uuid=test_wallet.uuid)

        assert len(balances) >= 1
        balance_ids = [b.id for b in balances]
        assert test_balance.id in balance_ids

    async def test_get_wallet_balances_exclude_zero(
        self, balance_manager: BalanceManager, test_wallet: Wallet, test_token: Token, test_chain: Chain
    ):
        """Test that zero balances are excluded by default"""
        # Create a zero balance
        zero_balance = Balance(
            wallet_id=test_wallet.id,
            token_id=test_token.id,
            chain_id=test_chain.id,
            amount=Decimal("0"),
            amount_decimal=Decimal("0"),
            price_usd=Decimal("2000.00"),
        )
        await zero_balance.save(balance_manager.db)

        # Get balances (should exclude zero)
        balances = await balance_manager.get_wallet_balances(wallet_uuid=test_wallet.uuid, include_zero=False)

        balance_amounts = [b.amount_decimal for b in balances]
        assert Decimal("0") not in balance_amounts

    async def test_get_wallet_balances_include_zero(
        self, balance_manager: BalanceManager, test_wallet: Wallet, test_token: Token, test_chain: Chain
    ):
        """Test that zero balances can be included"""
        # Create a zero balance
        zero_balance = Balance(
            wallet_id=test_wallet.id,
            token_id=test_token.id,
            chain_id=test_chain.id,
            amount=Decimal("0"),
            amount_decimal=Decimal("0"),
            price_usd=Decimal("2000.00"),
        )
        await zero_balance.save(balance_manager.db)

        # Get balances (include zero)
        balances = await balance_manager.get_wallet_balances(wallet_uuid=test_wallet.uuid, include_zero=True)

        balance_amounts = [b.amount_decimal for b in balances]
        assert Decimal("0") in balance_amounts

    async def test_get_wallet_balances_by_chain(
        self, balance_manager: BalanceManager, test_wallet: Wallet, test_chain: Chain, test_balance: Balance
    ):
        """Test getting balances for a specific chain"""
        balances = await balance_manager.get_wallet_balances_by_chain(test_wallet.id, test_chain.id)

        assert len(balances) >= 1
        for balance in balances:
            assert balance.chain_id == test_chain.id

    async def test_get_wallet_total_value(
        self, balance_manager: BalanceManager, test_wallet: Wallet, test_balance: Balance
    ):
        """Test calculating total wallet value"""
        totals = await balance_manager.get_wallet_total_value(test_wallet.id)

        assert "total_value_usd" in totals
        assert "token_count" in totals
        assert totals["token_count"] >= 1

    async def test_process_transaction(
        self, balance_manager: BalanceManager, test_wallet: Wallet, test_token: Token, test_chain: Chain
    ):
        """Test processing a transaction updates balance"""
        # Create a transaction
        tx = Transaction(
            wallet_id=test_wallet.id,
            token_id=test_token.id,
            chain_id=test_chain.id,
            transaction_type=TransactionType.BUY.value,
            amount=Decimal("5000000000000000000"),  # 5 ETH
            amount_decimal=Decimal("5.0"),
            price_usd=Decimal("2500.00"),
            transaction_hash="0xprocess123",
            timestamp=datetime.now(UTC),
            status=TransactionStatus.CONFIRMED.value,
        )
        await tx.save(balance_manager.db)

        # Process transaction
        balance = await balance_manager.process_transaction(tx, create_snapshot=False)

        assert balance is not None
        assert balance.wallet_id == test_wallet.id
        assert balance.token_id == test_token.id

    async def test_recalculate_wallet_balances(
        self,
        balance_manager: BalanceManager,
        test_wallet: Wallet,
        test_token: Token,
        test_chain: Chain,
        async_session: AsyncSession,
    ):
        """Test recalculating all balances for a wallet"""
        # Create multiple transactions
        for i in range(3):
            tx = Transaction(
                wallet_id=test_wallet.id,
                token_id=test_token.id,
                chain_id=test_chain.id,
                transaction_type=TransactionType.BUY.value,
                amount=Decimal("1000000000000000000"),  # 1 ETH
                amount_decimal=Decimal("1.0"),
                price_usd=Decimal(f"{2000 + i * 100}.00"),
                transaction_hash=f"0xrecalc{i}",
                timestamp=datetime.now(UTC),
                status=TransactionStatus.CONFIRMED.value,
            )
            await tx.save(async_session)

        # Recalculate balances
        balances = await balance_manager.recalculate_wallet_balances(test_wallet.id, create_snapshots=False)

        assert len(balances) >= 1
        # Check that balance reflects all transactions
        stmt = select(Balance).where(
            Balance.wallet_id == test_wallet.id,
            Balance.token_id == test_token.id,
            Balance.chain_id == test_chain.id,
        )
        result = await async_session.execute(stmt)
        balance = result.scalar_one()

        assert balance.amount_decimal == Decimal("3.0")  # 3 transactions of 1 ETH each

    async def test_update_prices(
        self, balance_manager: BalanceManager, test_balance: Balance, test_token: Token
    ):
        """Test updating price for all balances of a token"""
        new_price = Decimal("3000.00")

        updated_balances = await balance_manager.update_prices(
            test_token.id, new_price, create_snapshots=False
        )

        assert len(updated_balances) >= 1
        for balance in updated_balances:
            assert balance.price_usd == new_price

    async def test_balance_eager_loading(self, balance_manager: BalanceManager, test_balance: Balance):
        """Test that balance eager loads relationships"""
        balance = await balance_manager.get(test_balance.uuid)

        # Should have token, wallet, and chain loaded
        assert hasattr(balance, "token")
        assert balance.token is not None
        assert hasattr(balance, "wallet")
        assert balance.wallet is not None
        assert hasattr(balance, "chain")
        assert balance.chain is not None
