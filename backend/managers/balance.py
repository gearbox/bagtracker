from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from loguru import logger
from sqlalchemy import func, not_, select
from sqlalchemy.orm import selectinload

from backend.databases.models import Balance, Transaction, Wallet
from backend.managers import BaseCRUDManager
from backend.schemas import SnapshotType, TransactionStatus
from backend.services.balance_calculator import BalanceCalculator


class BalanceManager(BaseCRUDManager[Balance]):
    # Define relationships to eager load
    eager_load = [
        "token",
        "wallet",
        "chain",
    ]

    @property
    def _model_class(self) -> type[Balance]:
        return Balance

    async def get_wallet_balances(
        self,
        wallet_id: int | None = None,
        wallet_uuid: UUID | None = None,
        include_zero: bool = False,
        eager_load: list[str] | None = None,
    ) -> Sequence[Balance]:
        """
        Gets all balances for a wallet.

        Args:
            wallet_id: Internal wallet ID
            wallet_uuid: External wallet UUID
            include_zero: Whether to include zero balances

        Returns:
            List of Balance objects
        """
        if wallet_uuid:
            wallet = await Wallet.get_by_uuid(self.db, wallet_uuid)
            wallet_id = wallet.id

        stmt = self._get_by_kwargs(wallet_id=wallet_id)
        stmt = self._apply_eager_loading(stmt, eager_load=eager_load)

        if not include_zero:
            stmt = stmt.where(self.model.amount_decimal > 0)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_wallet_balances_by_chain(
        self, wallet_id: int, chain_id: int, include_zero: bool = False
    ) -> list[Balance]:
        """Get balances for a wallet on a specific chain."""
        stmt = (
            select(Balance)
            .where(Balance.wallet_id == wallet_id, Balance.chain_id == chain_id)
            .options(selectinload(Balance.token), selectinload(Balance.chain))
        )

        if not include_zero:
            stmt = stmt.where(Balance.amount_decimal > 0)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_wallet_total_value(self, wallet_id: int) -> dict:
        """
        Calculates total portfolio value for a wallet.

        Returns:
            Dict with total_value_usd and breakdown by token
        """
        stmt = select(
            func.sum(self.model.amount_decimal).label("amount_decimal"),
            func.sum(self.model.price_usd).label("price_usd"),
            # Weighted averages for buy/sell prices
            (
                func.sum(self.model.avg_buy_price_usd * self.model.total_bought_decimal)
                / func.nullif(func.sum(self.model.total_bought_decimal), 0)
            ).label("avg_buy_price_usd"),
            (
                func.sum(self.model.avg_sell_price_usd * self.model.total_sold_decimal)
                / func.nullif(func.sum(self.model.total_sold_decimal), 0)
            ).label("avg_sell_price_usd"),
            func.sum(self.model.total_bought_decimal).label("total_bought_decimal"),
            func.sum(self.model.total_sold_decimal).label("total_sold_decimal"),
            func.count(self.model.id).label("token_count"),
        ).where(
            self.model.wallet_id == wallet_id,
            self.model.amount_decimal > 0,
        )

        result = await self.db.execute(stmt)
        row = result.one()

        calculator = BalanceCalculator(self.db, self.settings)

        total_balance = Balance()
        total_balance._assign_attributes(row._asdict())

        totals = await calculator.calculate_from_balance(total_balance)

        return {
            **totals.model_dump(),
            "token_count": row.token_count or 0,
        }

    async def get_wallet_total_by_chain(self, wallet_id: int) -> dict[int, Decimal]:
        """
        Get total value per chain for a wallet.

        Returns:
            Dict mapping chain_id -> total_value_usd
        """
        from sqlalchemy import func

        stmt = (
            select(Balance.chain_id, func.sum(Balance.amount_decimal * Balance.price_usd).label("total_value_usd"))
            .where(Balance.wallet_id == wallet_id, Balance.amount_decimal > 0)
            .group_by(Balance.chain_id)
        )

        result = await self.db.execute(stmt)
        return {row.chain_id: row.total_value_usd for row in result}

    async def process_transaction(self, transaction: Transaction, create_snapshot: bool = True) -> Balance:
        """
        Processes a transaction and updates balances.
        This is the main integration point called when transactions are created.

        Args:
            transaction: Transaction to process
            create_snapshot: Whether to create history snapshot

        Returns:
            Updated Balance object
        """
        calculator = BalanceCalculator(self.db, self.settings)
        balance = await calculator.process_transaction(transaction=transaction, create_snapshot=create_snapshot)

        # Update wallet total value
        if transaction.wallet_id:
            await self._update_wallet_total(transaction.wallet_id)

        return balance

    async def _update_wallet_total(self, wallet_id: int) -> None:
        """Updates the total_value_usd on the wallet record."""
        totals = await self.get_wallet_total_value(wallet_id)
        logger.debug(f"{totals=}")

        stmt = select(Wallet).where(Wallet.id == wallet_id)
        result = await self.db.execute(stmt)
        wallet = result.scalar_one()

        wallet.total_value_usd = totals["total_value_usd"]
        logger.debug(f"Saving balance: {wallet.total_value_usd}")
        # await self.db.flush()
        await Wallet.save(wallet, self.db)

    async def recalculate_wallet_balances(self, wallet_id: int, create_snapshots: bool = False) -> list[Balance]:
        """
        Recalculates all balances for a wallet from scratch.
        Use this for corrections or after data migrations.

        WARNING: Expensive operation!

        Args:
            wallet_id: Wallet to recalculate
            create_snapshots: Whether to create history snapshots

        Returns:
            List of recalculated Balance objects (excludes None results)
        """
        calculator = BalanceCalculator(self.db, self.settings)

        # Get all unique token/chain combinations for this wallet
        stmt = (
            select(Transaction.token_id, Transaction.chain_id)
            .where(
                Transaction.wallet_id == wallet_id,
                Transaction.status == TransactionStatus.CONFIRMED.value,
                not_(Transaction.is_deleted),
            )
            .distinct()
        )

        result = await self.db.execute(stmt)
        token_chain_pairs = result.all()
        logger.debug(f"{token_chain_pairs=}")

        recalculated_balances = []

        for token_id, chain_id in token_chain_pairs:
            balance = await calculator.recalculate_balance_from_transactions(
                wallet_id=wallet_id, token_id=token_id, chain_id=chain_id
            )

            # Skip if no transactions exist for this token/chain
            if balance is None:
                continue

            if create_snapshots:
                await calculator._create_history_snapshot(
                    balance=balance, snapshot_type=SnapshotType.TRANSACTION, triggered_by="recalculation"
                )

            recalculated_balances.append(balance)

        # Update wallet total
        await self._update_wallet_total(wallet_id)

        return recalculated_balances

    async def update_prices(
        self,
        token_id: int,
        new_price_usd: Decimal,
        snapshot_type: SnapshotType = SnapshotType.HOURLY,
        create_snapshots: bool = False,
    ) -> Sequence[Balance]:
        """
        Updates price for all balances of a specific token.
        Used for scheduled price updates (hourly, daily, etc.)

        Args:
            token_id: Token to update
            new_price_usd: New price in USD
            snapshot_type: Type of snapshot to create (default: HOURLY)
            create_snapshots: Whether to create history snapshots

        Returns:
            List of updated Balance objects
        """
        calculator = BalanceCalculator(self.db, self.settings)

        stmt = select(self.model).where(self.model.token_id == token_id, self.model.amount_decimal > 0)

        result = await self.db.execute(stmt)
        balances = result.scalars().all()

        for balance in balances:
            balance.price_usd = new_price_usd
            balance.last_price_update = datetime.now(UTC)

            if create_snapshots:
                await calculator._create_history_snapshot(
                    balance=balance, snapshot_type=snapshot_type, triggered_by="price_update"
                )

        return balances
