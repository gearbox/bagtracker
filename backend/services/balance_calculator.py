"""
Balance Calculator Service
Handles balance calculations using FIFO cost basis method.
"""

from datetime import UTC, datetime
from decimal import Decimal

from loguru import logger
from sqlalchemy import not_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.databases.models import Balance, BalanceHistory, Transaction
from backend.errors import TransactionError
from backend.schemas import BalanceCalculatedTotals, SnapshotType, TransactionStatus, TransactionType
from backend.settings import Settings


class BalanceCalculator:
    """
    Calculates and maintains balance state using FIFO (First-In-First-Out) method.

    Key principles:
    - Immutability: Never modify past transactions or history records
    - Idempotency: Re-running calculations yields the same result
    - Atomicity: All balance updates happen in a single DB transaction

    Note: This is a service class instantiated by managers, not a FastAPI dependency.
    """

    qtz_default = Decimal("1.0000")

    def __init__(self, db: AsyncSession, settings: Settings):
        """
        Initialize balance calculator.

        Args:
            db: Database session (from manager)
            settings: Application settings (from manager)
        """
        self.db = db
        self.settings = settings
        self._dust_threshold = self.settings.balance_dust_threshold

    async def process_transaction(self, transaction: Transaction, create_snapshot: bool = True) -> Balance:
        """
        Main entry point: processes a transaction and updates balances.

        Args:
            transaction: The transaction to process
            create_snapshot: Whether to create a history snapshot (default: True)

        Returns:
            Updated Balance object
        """
        # TODO: move _get_or_create_balance to the TransactionManager/BalanceManager
        # Get or create balance record
        balance = await self._get_or_create_balance(transaction)

        # Calculate new balance based on transaction type
        balance = await self._apply_transaction(balance, transaction)

        # Create history snapshot if requested
        if create_snapshot:
            await self._create_history_snapshot(
                balance=balance, snapshot_type=SnapshotType.TRANSACTION, triggered_by=f"tx_{transaction.uuid}"
            )

        await self.db.flush()
        return balance

    async def _get_or_create_balance(self, transaction: Transaction) -> Balance:
        """Gets existing balance or creates a new one."""
        if transaction.wallet_id:
            # Wallet balance
            stmt = select(Balance).where(
                Balance.wallet_id == transaction.wallet_id,
                Balance.token_id == transaction.token_id,
                Balance.chain_id == transaction.chain_id,
            )
        else:
            # CEX balance - would need CexBalance model
            raise NotImplementedError("CEX balance calculation not yet implemented")

        result = await self.db.execute(stmt)
        balance = result.scalar_one_or_none()

        if not balance:
            # Create new balance record
            balance = Balance(
                wallet_id=transaction.wallet_id,
                chain_id=transaction.chain_id,
                token_id=transaction.token_id,
                amount=Decimal(0),
                amount_decimal=Decimal(0),
                avg_buy_price_usd=Decimal(0),
                price_usd=transaction.price_usd,
                last_price_update=transaction.timestamp,
            )
            # self.db.add(balance)
            # await self.db.flush()
            logger.debug("Saving Balance")
            await Balance.save(balance, self.db)

        return balance

    async def _apply_transaction(self, balance: Balance, transaction: Transaction) -> Balance:
        """
        Applies transaction to balance using FIFO cost basis method.

        Transaction types:
        - BUY / TRANSFER_IN: Increases balance, updates avg cost
        - SELL / TRANSFER_OUT: Decreases balance, realizes P&L
        """
        tx_type = TransactionType(transaction.transaction_type)
        tx_amount = transaction.amount
        tx_price = transaction.price_usd or Decimal(0)

        # Store previous balance for change tracking
        balance.previous_balance_decimal = balance.amount_decimal

        if tx_type in (TransactionType.BUY, TransactionType.TRANSFER_IN):
            await self._process_acquisition(balance, tx_amount, tx_price)

        elif tx_type in (TransactionType.SELL, TransactionType.TRANSFER_OUT):
            await self._process_disposal(balance, tx_amount, tx_price)

        # Update current price and value
        balance.price_usd = tx_price
        balance.last_price_update = transaction.timestamp
        balance.last_updated_at = datetime.now(UTC)

        return balance

    async def _process_acquisition(self, balance: Balance, amount: Decimal, buy_price: Decimal) -> None:
        """
        Processes BUY or TRANSFER_IN using FIFO method.
        Updates average buy price using weighted average.
        """
        # Convert raw amount to decimal (divide by 10^decimals)
        amount_decimal = amount

        current_value = balance.total_bought_decimal * balance.avg_buy_price_usd
        new_value = amount_decimal * buy_price
        total_bought = balance.total_bought_decimal + amount_decimal

        if total_bought > 0:
            balance.avg_buy_price_usd = (current_value + new_value) / total_bought
        else:
            balance.avg_buy_price_usd = buy_price

        # Update totals
        balance.total_bought_decimal += amount_decimal
        balance.amount_decimal += amount_decimal
        balance.amount += amount

    async def _process_disposal(self, balance: Balance, amount: Decimal, sell_price: Decimal) -> None:
        """
        Processes SELL or TRANSFER_OUT.
        Updates average sell price and realizes P&L.
        """
        amount_decimal = amount

        # Validate sufficient balance
        if balance.amount_decimal < amount_decimal:
            raise TransactionError(
                400,
                f"Insufficient balance: have {balance.amount_decimal.quantize(self.qtz_default)}, "
                f"trying to dispose {amount_decimal}",
            )

        # Update average sell price using weighted average
        current_sell_value = balance.total_sold_decimal * balance.avg_sell_price_usd
        new_sell_value = amount_decimal * sell_price
        total_sold = balance.total_sold_decimal + amount_decimal

        if total_sold > 0:
            balance.avg_sell_price_usd = (current_sell_value + new_sell_value) / total_sold
        else:
            balance.avg_sell_price_usd = sell_price

        # Update totals
        balance.total_sold_decimal += amount_decimal
        balance.amount_decimal -= amount_decimal
        balance.amount -= amount

        # If balance reaches dust threshold, reset
        if balance.amount_decimal <= self._dust_threshold:
            balance.amount_decimal = Decimal(0)
            balance.amount = Decimal(0)
            # Keep historical averages for reference

    async def _create_history_snapshot(
        self, balance: Balance, snapshot_type: SnapshotType, triggered_by: str | None = None
    ) -> BalanceHistory:
        """
        Creates a snapshot in the balance_history hypertable.

        Args:
            balance: Balance to snapshot
            snapshot_type: Type of snapshot (use SnapshotType enum)
            triggered_by: Optional trigger identifier
        """
        history = BalanceHistory(
            wallet_id=balance.wallet_id,
            chain_id=balance.chain_id,
            token_id=balance.token_id,
            amount=balance.amount,
            amount_decimal=balance.amount_decimal,
            price_usd=balance.price_usd,
            avg_buy_price_usd=balance.avg_buy_price_usd,
            last_price_update=balance.last_price_update,
            snapshot_date=datetime.now(UTC),
            snapshot_type=snapshot_type.value,  # Convert enum to string for DB
            triggered_by=triggered_by,
        )

        # self.db.add(history)
        await BalanceHistory.save(history, self.db)
        return history

    async def recalculate_balance_from_transactions(
        self, wallet_id: int, token_id: int, chain_id: int
    ) -> Balance | None:
        """
        Recalculates balance from scratch by replaying all transactions.
        Useful for corrections or after data inconsistencies.

        WARNING: This is expensive. Only use when necessary.

        Returns:
            Balance object if transactions exist, None if no transactions found
        """
        # Get all confirmed transactions ordered by timestamp
        stmt = (
            select(Transaction)
            .filter(
                Transaction.wallet_id == wallet_id,
                Transaction.token_id == token_id,
                Transaction.chain_id == chain_id,
                Transaction.status == TransactionStatus.CONFIRMED.value,
                not_(Transaction.is_deleted),
            )
            .order_by(Transaction.timestamp.asc())
        )

        result = await self.db.execute(stmt)
        transactions = result.scalars().all()

        # Handle case with no transactions
        if not transactions:
            # Check if balance exists and delete it (zero balance with no transactions)
            stmt = select(Balance).where(
                Balance.wallet_id == wallet_id, Balance.token_id == token_id, Balance.chain_id == chain_id
            )
            result = await self.db.execute(stmt)
            if existing_balance := result.scalar_one_or_none():
                await self.db.delete(existing_balance)
                await self.db.flush()

            return None

        # Get or create balance (will be reset)
        balance = await self._get_or_create_balance(transactions[0])

        # Reset balance to zero before recalculation
        balance.amount = Decimal(0)  # Raw amount as Decimal
        balance.amount_decimal = Decimal(0)
        balance.avg_buy_price_usd = Decimal(0)
        balance.avg_sell_price_usd = Decimal(0)
        balance.total_bought_decimal = Decimal(0)
        balance.total_sold_decimal = Decimal(0)

        # Replay all transactions
        for tx in transactions:
            logger.debug(f"Try to apply transaction {tx.to_dict()}")
            await self._apply_transaction(balance, tx)

        return balance

    async def calculate_from_balance(self, balance: Balance | dict) -> BalanceCalculatedTotals:
        if isinstance(balance, Balance):
            balance_price_usd = balance.price_usd or Decimal(0)
            balance_amount_decimal = balance.amount_decimal or Decimal(0)
            balance_avg_buy_price_usd = balance.avg_buy_price_usd or Decimal(0)
            balance_avg_sell_price_usd = balance.avg_sell_price_usd or Decimal(0)
            balance_total_sold_decimal = balance.total_sold_decimal or Decimal(0)
        else:
            balance_price_usd = balance["price_usd"] or Decimal(0)
            balance_amount_decimal = balance["amount_decimal"] or Decimal(0)
            balance_avg_buy_price_usd = balance["avg_buy_price_usd"] or Decimal(0)
            balance_avg_sell_price_usd = balance["avg_sell_price_usd"] or Decimal(0)
            balance_total_sold_decimal = balance.get("total_sold_decimal") or Decimal(0)

        balance_value_usd = balance_amount_decimal * balance_price_usd

        realized_pnl_usd = (
            (balance_avg_sell_price_usd - balance_avg_buy_price_usd) * balance_total_sold_decimal
            if balance_total_sold_decimal > 0
            else Decimal(0)
        )
        unrealized_pnl_usd = (balance_price_usd - balance_avg_buy_price_usd) * balance_amount_decimal
        unrealized_pnl_percent = (
            ((balance_price_usd - balance_avg_buy_price_usd) / balance_avg_buy_price_usd) * 100
            if balance_avg_buy_price_usd
            else Decimal(0)
        )
        return BalanceCalculatedTotals(
            total_value_usd_display=f"${balance_value_usd.quantize(self.qtz_default):,.2f}",
            total_value_usd=balance_value_usd.quantize(self.qtz_default),
            total_realized_pnl_usd=realized_pnl_usd.quantize(self.qtz_default),
            total_unrealized_pnl_usd=unrealized_pnl_usd.quantize(self.qtz_default),
            total_unrealized_pnl_percent=unrealized_pnl_percent.quantize(self.qtz_default),
        )

    async def calculate_from_balance_many(self, balances: list[Balance | dict]) -> list[BalanceCalculatedTotals]:
        return [await self.calculate_from_balance(balance) for balance in balances]
