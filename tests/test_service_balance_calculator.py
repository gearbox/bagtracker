"""Tests for BalanceCalculator service"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.databases.models import Balance, BalanceHistory, Chain, Token, Transaction, Wallet
from backend.errors import TransactionError
from backend.schemas import TransactionStatus, TransactionType
from backend.services.balance_calculator import BalanceCalculator
from backend.settings import Settings


@pytest.mark.asyncio
class TestBalanceCalculator:
    """Test BalanceCalculator service"""

    async def test_process_buy_transaction(
        self,
        async_session: AsyncSession,
        test_settings: Settings,
        test_wallet: Wallet,
        test_token: Token,
        test_chain: Chain,
    ):
        """Test processing a BUY transaction"""
        calculator = BalanceCalculator(async_session, test_settings)

        tx = Transaction(
            wallet_id=test_wallet.id,
            token_id=test_token.id,
            chain_id=test_chain.id,
            transaction_type=TransactionType.BUY.value,
            amount=Decimal("1000000000000000000"),  # 1 ETH
            amount_decimal=Decimal("1.0"),
            price_usd=Decimal("2000.00"),
            transaction_hash="0xbuy123",
            timestamp=datetime.now(UTC),
            status=TransactionStatus.CONFIRMED.value,
        )
        await tx.save(async_session)

        balance = await calculator.process_transaction(tx, create_snapshot=False)

        assert balance is not None
        assert balance.amount_decimal == Decimal("1.0")
        assert balance.avg_buy_price_usd == Decimal("2000.00")
        assert balance.total_bought_decimal == Decimal("1.0")

    async def test_process_sell_transaction(
        self,
        async_session: AsyncSession,
        test_settings: Settings,
        test_wallet: Wallet,
        test_token: Token,
        test_chain: Chain,
    ):
        """Test processing a SELL transaction"""
        calculator = BalanceCalculator(async_session, test_settings)

        # First buy some tokens
        buy_tx = Transaction(
            wallet_id=test_wallet.id,
            token_id=test_token.id,
            chain_id=test_chain.id,
            transaction_type=TransactionType.BUY.value,
            amount=Decimal("2000000000000000000"),  # 2 ETH
            amount_decimal=Decimal("2.0"),
            price_usd=Decimal("2000.00"),
            transaction_hash="0xbuy_before_sell",
            timestamp=datetime.now(UTC),
            status=TransactionStatus.CONFIRMED.value,
        )
        await buy_tx.save(async_session)
        await calculator.process_transaction(buy_tx, create_snapshot=False)

        # Then sell some
        sell_tx = Transaction(
            wallet_id=test_wallet.id,
            token_id=test_token.id,
            chain_id=test_chain.id,
            transaction_type=TransactionType.SELL.value,
            amount=Decimal("1000000000000000000"),  # 1 ETH
            amount_decimal=Decimal("1.0"),
            price_usd=Decimal("2500.00"),
            transaction_hash="0xsell123",
            timestamp=datetime.now(UTC),
            status=TransactionStatus.CONFIRMED.value,
        )
        await sell_tx.save(async_session)

        balance = await calculator.process_transaction(sell_tx, create_snapshot=False)

        assert balance.amount_decimal == Decimal("1.0")  # 2 - 1 = 1
        assert balance.total_sold_decimal == Decimal("1.0")
        assert balance.avg_sell_price_usd == Decimal("2500.00")

    async def test_process_sell_insufficient_balance(
        self,
        async_session: AsyncSession,
        test_settings: Settings,
        test_wallet: Wallet,
        test_token: Token,
        test_chain: Chain,
    ):
        """Test that selling more than balance raises error"""
        calculator = BalanceCalculator(async_session, test_settings)

        # Try to sell without buying first
        sell_tx = Transaction(
            wallet_id=test_wallet.id,
            token_id=test_token.id,
            chain_id=test_chain.id,
            transaction_type=TransactionType.SELL.value,
            amount=Decimal("1000000000000000000"),
            amount_decimal=Decimal("1.0"),
            price_usd=Decimal("2000.00"),
            transaction_hash="0xinsufficient",
            timestamp=datetime.now(UTC),
            status=TransactionStatus.CONFIRMED.value,
        )
        await sell_tx.save(async_session)

        with pytest.raises(TransactionError) as exc_info:
            await calculator.process_transaction(sell_tx, create_snapshot=False)

        assert "insufficient balance" in exc_info.value.exception_message.lower()

    async def test_process_transfer_in(
        self,
        async_session: AsyncSession,
        test_settings: Settings,
        test_wallet: Wallet,
        test_token: Token,
        test_chain: Chain,
    ):
        """Test processing a TRANSFER_IN transaction"""
        calculator = BalanceCalculator(async_session, test_settings)

        tx = Transaction(
            wallet_id=test_wallet.id,
            token_id=test_token.id,
            chain_id=test_chain.id,
            transaction_type=TransactionType.TRANSFER_IN.value,
            amount=Decimal("3000000000000000000"),  # 3 ETH
            amount_decimal=Decimal("3.0"),
            price_usd=Decimal("2100.00"),
            transaction_hash="0xtransferin123",
            timestamp=datetime.now(UTC),
            status=TransactionStatus.CONFIRMED.value,
        )
        await tx.save(async_session)

        balance = await calculator.process_transaction(tx, create_snapshot=False)

        assert balance.amount_decimal == Decimal("3.0")
        assert balance.total_bought_decimal == Decimal("3.0")

    async def test_process_transfer_out(
        self,
        async_session: AsyncSession,
        test_settings: Settings,
        test_wallet: Wallet,
        test_token: Token,
        test_chain: Chain,
    ):
        """Test processing a TRANSFER_OUT transaction"""
        calculator = BalanceCalculator(async_session, test_settings)

        # First transfer in some tokens
        transfer_in = Transaction(
            wallet_id=test_wallet.id,
            token_id=test_token.id,
            chain_id=test_chain.id,
            transaction_type=TransactionType.TRANSFER_IN.value,
            amount=Decimal("5000000000000000000"),  # 5 ETH
            amount_decimal=Decimal("5.0"),
            price_usd=Decimal("2000.00"),
            transaction_hash="0xtransferin_before_out",
            timestamp=datetime.now(UTC),
            status=TransactionStatus.CONFIRMED.value,
        )
        await transfer_in.save(async_session)
        await calculator.process_transaction(transfer_in, create_snapshot=False)

        # Then transfer out some
        transfer_out = Transaction(
            wallet_id=test_wallet.id,
            token_id=test_token.id,
            chain_id=test_chain.id,
            transaction_type=TransactionType.TRANSFER_OUT.value,
            amount=Decimal("2000000000000000000"),  # 2 ETH
            amount_decimal=Decimal("2.0"),
            price_usd=Decimal("2100.00"),
            transaction_hash="0xtransferout123",
            timestamp=datetime.now(UTC),
            status=TransactionStatus.CONFIRMED.value,
        )
        await transfer_out.save(async_session)

        balance = await calculator.process_transaction(transfer_out, create_snapshot=False)

        assert balance.amount_decimal == Decimal("3.0")  # 5 - 2 = 3
        assert balance.total_sold_decimal == Decimal("2.0")

    async def test_fifo_cost_basis_calculation(
        self,
        async_session: AsyncSession,
        test_settings: Settings,
        test_wallet: Wallet,
        test_token: Token,
        test_chain: Chain,
    ):
        """Test FIFO cost basis calculation with multiple buys"""
        calculator = BalanceCalculator(async_session, test_settings)

        # Buy 1 ETH at $2000
        buy1 = Transaction(
            wallet_id=test_wallet.id,
            token_id=test_token.id,
            chain_id=test_chain.id,
            transaction_type=TransactionType.BUY.value,
            amount=Decimal("1000000000000000000"),
            amount_decimal=Decimal("1.0"),
            price_usd=Decimal("2000.00"),
            transaction_hash="0xfifobuy1",
            timestamp=datetime.now(UTC),
            status=TransactionStatus.CONFIRMED.value,
        )
        await buy1.save(async_session)
        await calculator.process_transaction(buy1, create_snapshot=False)

        # Buy 2 ETH at $2500
        buy2 = Transaction(
            wallet_id=test_wallet.id,
            token_id=test_token.id,
            chain_id=test_chain.id,
            transaction_type=TransactionType.BUY.value,
            amount=Decimal("2000000000000000000"),
            amount_decimal=Decimal("2.0"),
            price_usd=Decimal("2500.00"),
            transaction_hash="0xfifobuy2",
            timestamp=datetime.now(UTC),
            status=TransactionStatus.CONFIRMED.value,
        )
        await buy2.save(async_session)
        balance = await calculator.process_transaction(buy2, create_snapshot=False)

        # Average should be (1*2000 + 2*2500) / 3 = 7000 / 3 = 2333.33...
        expected_avg = (Decimal("1.0") * Decimal("2000.00") + Decimal("2.0") * Decimal("2500.00")) / Decimal("3.0")
        assert balance.avg_buy_price_usd == expected_avg
        assert balance.amount_decimal == Decimal("3.0")

    async def test_create_history_snapshot(
        self,
        async_session: AsyncSession,
        test_settings: Settings,
        test_wallet: Wallet,
        test_token: Token,
        test_chain: Chain,
    ):
        """Test creating balance history snapshot"""
        calculator = BalanceCalculator(async_session, test_settings)

        # Create a transaction with snapshot
        tx = Transaction(
            wallet_id=test_wallet.id,
            token_id=test_token.id,
            chain_id=test_chain.id,
            transaction_type=TransactionType.BUY.value,
            amount=Decimal("1000000000000000000"),
            amount_decimal=Decimal("1.0"),
            price_usd=Decimal("2000.00"),
            transaction_hash="0xsnapshot123",
            timestamp=datetime.now(UTC),
            status=TransactionStatus.CONFIRMED.value,
        )
        await tx.save(async_session)

        await calculator.process_transaction(tx, create_snapshot=True)

        # Check that history was created
        stmt = select(BalanceHistory).where(
            BalanceHistory.wallet_id == test_wallet.id,
            BalanceHistory.token_id == test_token.id,
            BalanceHistory.chain_id == test_chain.id,
        )
        result = await async_session.execute(stmt)
        history = result.scalar_one_or_none()

        assert history is not None
        assert history.amount_decimal == Decimal("1.0")

    async def test_recalculate_balance_from_transactions(
        self,
        async_session: AsyncSession,
        test_settings: Settings,
        test_wallet: Wallet,
        test_token: Token,
        test_chain: Chain,
    ):
        """Test recalculating balance from all transactions"""
        calculator = BalanceCalculator(async_session, test_settings)

        # Create multiple transactions
        transactions_data = [
            (TransactionType.BUY, Decimal("1.0"), Decimal("2000.00")),
            (TransactionType.BUY, Decimal("2.0"), Decimal("2500.00")),
            (TransactionType.SELL, Decimal("1.0"), Decimal("3000.00")),
        ]

        for i, (tx_type, amount, price) in enumerate(transactions_data):
            tx = Transaction(
                wallet_id=test_wallet.id,
                token_id=test_token.id,
                chain_id=test_chain.id,
                transaction_type=tx_type.value,
                amount=amount * Decimal("1000000000000000000"),
                amount_decimal=amount,
                price_usd=price,
                transaction_hash=f"0xrecalc{i}",
                timestamp=datetime.now(UTC),
                status=TransactionStatus.CONFIRMED.value,
            )
            await tx.save(async_session)

        # Recalculate from scratch
        balance = await calculator.recalculate_balance_from_transactions(
            test_wallet.id, test_token.id, test_chain.id
        )

        assert balance is not None
        # Should have 1 + 2 - 1 = 2 ETH
        assert balance.amount_decimal == Decimal("2.0")
        assert balance.total_bought_decimal == Decimal("3.0")
        assert balance.total_sold_decimal == Decimal("1.0")

    async def test_recalculate_with_no_transactions(
        self,
        async_session: AsyncSession,
        test_settings: Settings,
        test_wallet: Wallet,
        test_token: Token,
        test_chain: Chain,
    ):
        """Test recalculating when no transactions exist"""
        calculator = BalanceCalculator(async_session, test_settings)

        # Recalculate with no transactions
        balance = await calculator.recalculate_balance_from_transactions(
            test_wallet.id, test_token.id, test_chain.id
        )

        # Should return None when no transactions
        assert balance is None

    async def test_dust_threshold(
        self,
        async_session: AsyncSession,
        test_settings: Settings,
        test_wallet: Wallet,
        test_token: Token,
        test_chain: Chain,
    ):
        """Test that balances below dust threshold are zeroed"""
        calculator = BalanceCalculator(async_session, test_settings)

        # Buy a small amount
        buy_tx = Transaction(
            wallet_id=test_wallet.id,
            token_id=test_token.id,
            chain_id=test_chain.id,
            transaction_type=TransactionType.BUY.value,
            amount=Decimal("1000000000000000"),  # 0.001 ETH
            amount_decimal=Decimal("0.001"),
            price_usd=Decimal("2000.00"),
            transaction_hash="0xdustbuy",
            timestamp=datetime.now(UTC),
            status=TransactionStatus.CONFIRMED.value,
        )
        await buy_tx.save(async_session)
        await calculator.process_transaction(buy_tx, create_snapshot=False)

        # Sell almost all of it, leaving dust
        sell_tx = Transaction(
            wallet_id=test_wallet.id,
            token_id=test_token.id,
            chain_id=test_chain.id,
            transaction_type=TransactionType.SELL.value,
            amount=Decimal("999999000000000"),  # 0.000999999 ETH (leaves 0.000001)
            amount_decimal=Decimal("0.000999"),
            price_usd=Decimal("2500.00"),
            transaction_hash="0xdustsell",
            timestamp=datetime.now(UTC),
            status=TransactionStatus.CONFIRMED.value,
        )
        await sell_tx.save(async_session)
        balance = await calculator.process_transaction(sell_tx, create_snapshot=False)

        # Balance should be zeroed out due to dust threshold
        assert balance.amount_decimal == Decimal("0")

    async def test_calculate_from_balance(
        self, async_session: AsyncSession, test_settings: Settings, test_balance: Balance
    ):
        """Test calculating totals from a balance"""
        calculator = BalanceCalculator(async_session, test_settings)

        totals = await calculator.calculate_from_balance(test_balance)

        assert totals.total_value_usd > 0
        assert "total_value_usd_display" in totals.model_dump()
