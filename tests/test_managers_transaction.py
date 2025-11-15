"""Tests for TransactionManager"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.databases.models import Chain, Token, Transaction, Wallet
from backend.errors import DatabaseError
from backend.managers import TransactionManager
from backend.schemas import TransactionCreateOrUpdate, TransactionStatus, TransactionType


@pytest.mark.asyncio
class TestTransactionManager:
    """Test TransactionManager CRUD operations"""

    async def test_create_transaction(
        self, transaction_manager: TransactionManager, test_wallet: Wallet, test_token: Token, test_chain: Chain
    ):
        """Test creating a transaction"""
        tx_data = TransactionCreateOrUpdate(
            wallet_uuid=test_wallet.uuid,
            token_id=test_token.id,
            chain_id=test_chain.id,
            transaction_type=TransactionType.BUY,
            amount=Decimal("1000000000000000000"),  # 1 ETH
            amount_decimal=Decimal("1.0"),
            price_usd=Decimal("2000.50"),
            transaction_hash="0xtest123456",
            block_number=12345678,
            timestamp=datetime.now(UTC),
            status=TransactionStatus.CONFIRMED,
        )

        tx = await transaction_manager.create_tx(tx_data, process_balance=False)

        assert tx.id is not None
        assert tx.wallet_id == test_wallet.id
        assert tx.token_id == test_token.id
        assert tx.chain_id == test_chain.id
        assert tx.transaction_type == TransactionType.BUY.value
        assert tx.amount == Decimal("1000000000000000000")
        assert tx.price_usd == Decimal("2000.50")
        assert tx.status == TransactionStatus.CONFIRMED.value

    async def test_create_transaction_with_balance_processing(
        self, transaction_manager: TransactionManager, test_wallet: Wallet, test_token: Token, test_chain: Chain
    ):
        """Test creating a transaction that processes balances"""
        tx_data = TransactionCreateOrUpdate(
            wallet_uuid=test_wallet.uuid,
            token_id=test_token.id,
            chain_id=test_chain.id,
            transaction_type=TransactionType.BUY,
            amount=Decimal("2000000000000000000"),  # 2 ETH
            amount_decimal=Decimal("2.0"),
            price_usd=Decimal("2100.00"),
            transaction_hash="0xtest789",
            timestamp=datetime.now(UTC),
            status=TransactionStatus.CONFIRMED,
        )

        tx = await transaction_manager.create_tx(tx_data, process_balance=True)

        assert tx.id is not None
        # Balance should have been created/updated
        from backend.databases.models import Balance
        from sqlalchemy import select

        stmt = select(Balance).where(
            Balance.wallet_id == test_wallet.id,
            Balance.token_id == test_token.id,
            Balance.chain_id == test_chain.id,
        )
        result = await transaction_manager.db.execute(stmt)
        balance = result.scalar_one_or_none()

        assert balance is not None
        assert balance.amount_decimal == Decimal("2.0")

    async def test_get_transaction_by_uuid(
        self, transaction_manager: TransactionManager, test_transaction_buy: Transaction
    ):
        """Test getting transaction by UUID"""
        tx = await transaction_manager.get(test_transaction_buy.uuid)

        assert tx.id == test_transaction_buy.id
        assert tx.uuid == test_transaction_buy.uuid

    async def test_get_by_wallet_uuid(
        self, transaction_manager: TransactionManager, test_wallet: Wallet, test_transaction_buy: Transaction
    ):
        """Test getting all transactions for a wallet"""
        transactions = await transaction_manager.get_by_wallet_uuid(str(test_wallet.uuid))

        assert len(transactions) >= 1
        tx_ids = [tx.id for tx in transactions]
        assert test_transaction_buy.id in tx_ids

    async def test_update_transaction(
        self, transaction_manager: TransactionManager, test_transaction_buy: Transaction
    ):
        """Test updating a transaction"""
        update_data = TransactionCreateOrUpdate(
            wallet_uuid=test_transaction_buy.wallet.uuid,
            token_id=test_transaction_buy.token_id,
            chain_id=test_transaction_buy.chain_id,
            transaction_type=TransactionType.BUY,
            amount=Decimal("1500000000000000000"),  # Updated amount
            amount_decimal=Decimal("1.5"),
            price_usd=Decimal("2100.00"),  # Updated price
            transaction_hash=test_transaction_buy.transaction_hash,
            timestamp=test_transaction_buy.timestamp,
            status=TransactionStatus.CONFIRMED,
        )

        updated_tx = await transaction_manager.update_tx(
            test_transaction_buy.uuid, update_data, recalculate_balance=False
        )

        assert updated_tx.amount == Decimal("1500000000000000000")
        assert updated_tx.price_usd == Decimal("2100.00")

    async def test_mark_as_cancelled(
        self, transaction_manager: TransactionManager, test_transaction_buy: Transaction
    ):
        """Test marking a transaction as cancelled"""
        cancelled_tx = await transaction_manager.mark_as_cancelled(str(test_transaction_buy.uuid))

        assert cancelled_tx.status == TransactionStatus.CANCELLED.value

    async def test_delete_transaction(
        self, transaction_manager: TransactionManager, test_transaction_buy: Transaction
    ):
        """Test deleting a transaction"""
        await transaction_manager.delete_tx(str(test_transaction_buy.uuid), recalculate_balance=False)

        # Transaction should not be found
        with pytest.raises(DatabaseError):
            await transaction_manager.get(test_transaction_buy.uuid)

    async def test_bulk_create_transactions(
        self, transaction_manager: TransactionManager, test_wallet: Wallet, test_token: Token, test_chain: Chain
    ):
        """Test bulk creating multiple transactions"""
        tx_data_list = [
            TransactionCreateOrUpdate(
                wallet_uuid=test_wallet.uuid,
                token_id=test_token.id,
                chain_id=test_chain.id,
                transaction_type=TransactionType.BUY,
                amount=Decimal("1000000000000000000"),
                amount_decimal=Decimal("1.0"),
                price_usd=Decimal("2000.00"),
                transaction_hash=f"0xbulk{i}",
                timestamp=datetime.now(UTC),
                status=TransactionStatus.CONFIRMED,
            )
            for i in range(3)
        ]

        transactions = await transaction_manager.bulk_create_transactions(tx_data_list, process_balances=False)

        assert len(transactions) == 3
        for tx in transactions:
            assert tx.id is not None

    async def test_transaction_eager_loading(
        self, transaction_manager: TransactionManager, test_transaction_buy: Transaction
    ):
        """Test that transaction eager loads relationships"""
        tx = await transaction_manager.get(test_transaction_buy.uuid)

        # Should have wallet, token, and chain loaded
        assert hasattr(tx, "wallet")
        assert tx.wallet is not None
        assert hasattr(tx, "token")
        assert tx.token is not None
        assert hasattr(tx, "chain")
        assert tx.chain is not None
