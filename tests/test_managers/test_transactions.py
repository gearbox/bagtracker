"""
Tests for TransactionManager.

Tests transaction management functionality:
- create_tx()
- get_by_wallet_uuid()
- update_tx()
- delete_tx()
- mark_as_cancelled()
- bulk_create_transactions()
"""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.errors import BadRequestException
from backend.managers.transactions import TransactionManager
from backend.schemas import TransactionCreateOrUpdate, TransactionType
from backend.settings import get_settings


@pytest.mark.asyncio
class TestTransactionManagerCreate:
    """Test transaction creation."""

    async def test_create_tx_for_wallet(
        self, async_session: AsyncSession, user_factory, wallet_factory, chain_factory, token_factory
    ):
        """Test creating transaction for wallet."""
        settings = get_settings()
        manager = TransactionManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        wallet = wallet_factory(user.id)
        await wallet.save(async_session)

        chain = chain_factory()
        await chain.save(async_session)

        token = token_factory(chain.id)
        await token.save(async_session)

        from datetime import UTC, datetime

        tx_data = TransactionCreateOrUpdate(
            wallet_uuid=wallet.uuid,
            token_id=token.id,
            chain_id=chain.id,
            transaction_type=TransactionType.BUY,
            amount=Decimal("1000000000000000000"),
            price_usd=Decimal("100.0"),
            transaction_hash="0xABC123",
            timestamp=datetime.now(UTC),
        )

        created = await manager.create_tx(tx_data, process_balance=False)

        assert created.id is not None
        assert created.wallet_id == wallet.id
        assert created.token_id == token.id
        assert created.chain_id == chain.id
        assert created.transaction_type == TransactionType.BUY.value
        assert created.amount == Decimal("1000000000000000000")

    async def test_create_tx_requires_wallet_or_cex(self, async_session: AsyncSession, chain_factory, token_factory):
        """Test creating transaction requires either wallet_uuid or cex_account_uuid."""
        settings = get_settings()
        manager = TransactionManager(async_session, settings)

        chain = chain_factory()
        await chain.save(async_session)

        token = token_factory(chain.id)
        await token.save(async_session)

        from datetime import UTC, datetime

        # No wallet_uuid or cex_account_uuid
        tx_data = TransactionCreateOrUpdate(
            token_id=token.id,
            chain_id=chain.id,
            transaction_type=TransactionType.BUY,
            amount=Decimal("1.0"),
            price_usd=Decimal("100.0"),
            transaction_hash="0xABC123",
            timestamp=datetime.now(UTC),
        )

        with pytest.raises(BadRequestException):
            await manager.create_tx(tx_data)

    async def test_get_by_wallet_uuid(
        self, async_session: AsyncSession, user_factory, wallet_factory, chain_factory, token_factory
    ):
        """Test retrieving transactions by wallet UUID."""
        settings = get_settings()
        manager = TransactionManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        wallet = wallet_factory(user.id)
        await wallet.save(async_session)

        chain = chain_factory()
        await chain.save(async_session)

        token = token_factory(chain.id)
        await token.save(async_session)

        from datetime import UTC, datetime

        # Create multiple transactions
        tx_data1 = TransactionCreateOrUpdate(
            wallet_uuid=wallet.uuid,
            token_id=token.id,
            chain_id=chain.id,
            transaction_type=TransactionType.BUY,
            amount=Decimal("1.0"),
            price_usd=Decimal("100.0"),
            transaction_hash="0xTX1",
            timestamp=datetime.now(UTC),
        )

        tx_data2 = TransactionCreateOrUpdate(
            wallet_uuid=wallet.uuid,
            token_id=token.id,
            chain_id=chain.id,
            transaction_type=TransactionType.SELL,
            amount=Decimal("0.5"),
            price_usd=Decimal("105.0"),
            transaction_hash="0xTX2",
            timestamp=datetime.now(UTC),
        )

        await manager.create_tx(tx_data1, process_balance=False)
        await manager.create_tx(tx_data2, process_balance=False)

        # Get all transactions for wallet
        transactions = await manager.get_by_wallet_uuid(str(wallet.uuid))

        assert len(transactions) == 2
        tx_hashes = [tx.transaction_hash for tx in transactions]
        assert "0xTX1" in tx_hashes
        assert "0xTX2" in tx_hashes


@pytest.mark.asyncio
class TestTransactionManagerUpdate:
    """Test transaction updates and cancellation."""

    async def test_update_tx(
        self, async_session: AsyncSession, user_factory, wallet_factory, chain_factory, token_factory
    ):
        """Test updating transaction."""
        settings = get_settings()
        manager = TransactionManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        wallet = wallet_factory(user.id)
        await wallet.save(async_session)

        chain = chain_factory()
        await chain.save(async_session)

        token = token_factory(chain.id)
        await token.save(async_session)

        from datetime import UTC, datetime

        tx_data = TransactionCreateOrUpdate(
            wallet_uuid=wallet.uuid,
            token_id=token.id,
            chain_id=chain.id,
            transaction_type=TransactionType.BUY,
            amount=Decimal("1.0"),
            price_usd=Decimal("100.0"),
            transaction_hash="0xORIGINAL",
            timestamp=datetime.now(UTC),
        )

        created = await manager.create_tx(tx_data, process_balance=False)

        # Update price
        update_data = TransactionCreateOrUpdate(
            wallet_uuid=wallet.uuid,
            token_id=token.id,
            chain_id=chain.id,
            transaction_type=TransactionType.BUY,
            amount=Decimal("1.0"),
            price_usd=Decimal("110.0"),
            transaction_hash="0xORIGINAL",
            timestamp=created.timestamp,
        )

        updated = await manager.update_tx(created.uuid, update_data, recalculate_balance=False)

        assert updated.id == created.id
        assert updated.price_usd == Decimal("110.0")

    async def test_mark_as_cancelled(
        self, async_session: AsyncSession, user_factory, wallet_factory, chain_factory, token_factory
    ):
        """Test marking transaction as cancelled."""
        settings = get_settings()
        manager = TransactionManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        wallet = wallet_factory(user.id)
        await wallet.save(async_session)

        chain = chain_factory()
        await chain.save(async_session)

        token = token_factory(chain.id)
        await token.save(async_session)

        from datetime import UTC, datetime

        tx_data = TransactionCreateOrUpdate(
            wallet_uuid=wallet.uuid,
            token_id=token.id,
            chain_id=chain.id,
            transaction_type=TransactionType.BUY,
            amount=Decimal("1.0"),
            price_usd=Decimal("100.0"),
            transaction_hash="0xCANCEL",
            timestamp=datetime.now(UTC),
        )

        created = await manager.create_tx(tx_data, process_balance=False)

        # Mark as cancelled
        cancelled = await manager.mark_as_cancelled(str(created.uuid))

        assert cancelled.id == created.id
        assert cancelled.status == "cancelled"

    async def test_delete_tx(
        self, async_session: AsyncSession, user_factory, wallet_factory, chain_factory, token_factory
    ):
        """Test deleting transaction."""
        settings = get_settings()
        manager = TransactionManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        wallet = wallet_factory(user.id)
        await wallet.save(async_session)

        chain = chain_factory()
        await chain.save(async_session)

        token = token_factory(chain.id)
        await token.save(async_session)

        from datetime import UTC, datetime

        tx_data = TransactionCreateOrUpdate(
            wallet_uuid=wallet.uuid,
            token_id=token.id,
            chain_id=chain.id,
            transaction_type=TransactionType.BUY,
            amount=Decimal("1.0"),
            price_usd=Decimal("100.0"),
            transaction_hash="0xDELETE",
            timestamp=datetime.now(UTC),
        )

        created = await manager.create_tx(tx_data, process_balance=False)

        # Delete transaction
        await manager.delete_tx(str(created.uuid), recalculate_balance=False)

        # Should be soft deleted
        from backend.databases.models import Transaction

        deleted = await Transaction.get_by_uuid(async_session, created.uuid, include_deleted=True)
        assert deleted.is_deleted is True


@pytest.mark.asyncio
class TestTransactionManagerBulk:
    """Test bulk transaction operations."""

    async def test_bulk_create_transactions(
        self, async_session: AsyncSession, user_factory, wallet_factory, chain_factory, token_factory
    ):
        """Test bulk creating transactions."""
        settings = get_settings()
        manager = TransactionManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        wallet = wallet_factory(user.id)
        await wallet.save(async_session)

        chain = chain_factory()
        await chain.save(async_session)

        token = token_factory(chain.id)
        await token.save(async_session)

        from datetime import UTC, datetime

        # Create multiple transactions
        tx_list = [
            TransactionCreateOrUpdate(
                wallet_uuid=wallet.uuid,
                token_id=token.id,
                chain_id=chain.id,
                transaction_type=TransactionType.BUY,
                amount=Decimal(f"{i}.0"),
                price_usd=Decimal("100.0"),
                transaction_hash=f"0xBULK{i}",
                timestamp=datetime.now(UTC),
            )
            for i in range(1, 6)
        ]

        created_txs = await manager.bulk_create_transactions(tx_list, process_balances=False)

        assert len(created_txs) == 5
        for i, tx in enumerate(created_txs, 1):
            assert tx.transaction_hash == f"0xBULK{i}"
