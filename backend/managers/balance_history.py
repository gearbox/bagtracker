from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select

from backend.databases.models import BalanceHistory
from backend.managers.base_crud import BaseCRUDManager
from backend.schemas import PortfolioHistoryPoint, SnapshotType
from backend.services.balance_calculator import BalanceCalculator


class BalanceHistoryManager(BaseCRUDManager[BalanceHistory]):
    """Manager for balance history operations."""

    @property
    def _model_class(self) -> type[BalanceHistory]:
        return BalanceHistory

    async def get_balance_history(
        self,
        wallet_id: int,
        token_id: int,
        chain_id: int,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        snapshot_type: SnapshotType | None = None,
    ) -> Sequence[BalanceHistory]:
        """
        Gets balance history for charting and analytics.
        Leverages TimescaleDB hypertable for efficient time-series queries.

        Args:
            wallet_id: Wallet ID
            token_id: Token ID
            chain_id: Chain ID
            start_date: Start date filter
            end_date: End date filter
            snapshot_type: Type of snapshot filter (use SnapshotType enum)

        Returns:
            List of BalanceHistory records
        """
        stmt = (
            select(self.model)
            .filter(
                self.model.wallet_id == wallet_id,
                self.model.token_id == token_id,
                self.model.chain_id == chain_id,
            )
            .order_by(self.model.snapshot_date.asc())
        )

        if start_date:
            stmt = stmt.where(self.model.snapshot_date >= start_date)

        if end_date:
            stmt = stmt.where(self.model.snapshot_date <= end_date)

        if snapshot_type:
            stmt = stmt.where(self.model.snapshot_type == snapshot_type.value)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_portfolio_history_aggregated(
        self,
        wallet_id: int,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        snapshot_type: SnapshotType = SnapshotType.DAILY,
    ) -> list["PortfolioHistoryPoint"]:
        """
        Gets aggregated portfolio value over time.
        Perfect for portfolio charts.

        Args:
            wallet_id: Wallet ID
            start_date: Start date filter
            end_date: End date filter
            snapshot_type: Snapshot aggregation level (default: DAILY)

        Returns:
            List of PortfolioHistoryPoint objects with aggregated data
        """

        stmt = (
            select(
                self.model.snapshot_date,
                func.sum(self.model.amount_decimal).label("amount_decimal"),
                func.sum(self.model.price_usd).label("price_usd"),
                func.sum(self.model.avg_price_usd).label("avg_price_usd"),
            )
            .filter(
                self.model.wallet_id == wallet_id,
                self.model.snapshot_type == snapshot_type.value,
            )
            .group_by(self.model.snapshot_date)
            .order_by(self.model.snapshot_date.asc())
        )

        if start_date:
            stmt = stmt.filter(self.model.snapshot_date >= start_date)

        if end_date:
            stmt = stmt.filter(self.model.snapshot_date <= end_date)

        results = await self.db.execute(stmt)

        calculator = BalanceCalculator(self.db, self.settings)

        return [
            PortfolioHistoryPoint(
                snapshot_date=result.snapshot_date,
                **(await calculator.calculate_from_balance(result._asdict())).model_dump(),
            )
            for result in results
        ]
