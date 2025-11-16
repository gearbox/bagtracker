"""
Background tasks for balance snapshots and transaction processing.

This module defines Taskiq tasks for periodic operations:
- Balance snapshot creation (hourly, daily, weekly, monthly)
- Transaction recalculation
- Price updates with snapshots
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.databases.factory_async import get_async_db_instance
from backend.databases.models import Balance, Wallet
from backend.managers.balance import BalanceManager
from backend.schemas import SnapshotType
from backend.services.balance_calculator import BalanceCalculator
from backend.settings import get_settings
from backend.taskiq_broker import broker

settings = get_settings()


def _create_snapshot_task(
    snapshot_type: SnapshotType,
    schedule_name: str,  # e.g. "balance_hourly_snapshots"
    cron: str,
    triggered_by: str,  # e.g. "scheduled_hourly"
    task_id: str,  # same id as broker.task
) -> Callable[[], Any]:
    """
    Factory function to create snapshot tasks.

    Args:
        snapshot_type: Type of snapshot (HOURLY, DAILY, etc.)
        schedule_name: Name of the settings attribute for this schedule
        cron: Cron expression for scheduling
        triggered_by: String identifier for the trigger
        task_id: Unique task ID for the scheduler

    Returns:
        Decorated task function
    """

    @broker.task(schedule=[{"cron": cron, "id": task_id}])
    async def _inner() -> dict:
        if not settings.balance_snapshot_enabled or not getattr(settings, schedule_name):
            logger.info(f"{snapshot_type.value.capitalize()} snapshots disabled")
            return {"status": "skipped", "reason": "disabled_in_settings"}

        logger.info(f"Starting {snapshot_type.value} balance snapshots task")
        start = datetime.now(UTC)
        try:
            db = get_async_db_instance()
            async with db.session() as session:
                calculator = BalanceCalculator(db=session, settings=settings)
                stmt = select(Balance).where(Balance.amount_decimal > 0)
                result = await session.execute(stmt)
                balances = result.scalars().all()

                for b in balances:
                    await calculator._create_history_snapshot(
                        balance=b,
                        snapshot_type=snapshot_type,
                        triggered_by=triggered_by,
                    )
                await session.commit()

            duration = (datetime.now(UTC) - start).total_seconds()
            logger.info(f"{snapshot_type.value.capitalize()} snapshots completed: {len(balances)} in {duration:.2f}s")
            return {
                "status": "success",
                "snapshot_type": snapshot_type.value,
                "snapshots_created": len(balances),
                "duration_seconds": duration,
            }

        except Exception as e:
            logger.error(f"{snapshot_type.value.capitalize()} snapshot task failed: {e}")
            return {"status": "error", "error": str(e)}

    return _inner


# Create snapshot tasks using the factory function
create_hourly_snapshots = _create_snapshot_task(
    snapshot_type=SnapshotType.HOURLY,
    schedule_name="balance_hourly_snapshots",
    cron="5 * * * *",
    triggered_by="scheduled_hourly",
    task_id="hourly_balance_snapshots",
)

create_daily_snapshots = _create_snapshot_task(
    snapshot_type=SnapshotType.DAILY,
    schedule_name="balance_daily_snapshots",
    cron="15 0 * * *",
    triggered_by="scheduled_daily",
    task_id="daily_balance_snapshots",
)

create_weekly_snapshots = _create_snapshot_task(
    snapshot_type=SnapshotType.WEEKLY,
    schedule_name="balance_snapshot_enabled",  # No specific weekly setting, use main flag
    cron="0 1 * * 0",
    triggered_by="scheduled_weekly",
    task_id="weekly_balance_snapshots",
)

create_monthly_snapshots = _create_snapshot_task(
    snapshot_type=SnapshotType.MONTHLY,
    schedule_name="balance_snapshot_enabled",  # No specific monthly setting, use main flag
    cron="0 2 1 * *",
    triggered_by="scheduled_monthly",
    task_id="monthly_balance_snapshots",
)


@broker.task
async def recalculate_wallet_balances(wallet_id: int, create_snapshots: bool = False) -> dict:
    """
    Recalculate all balances for a specific wallet from transactions.

    This is an expensive operation that replays all transactions to recalculate
    balances from scratch. Use sparingly for corrections or after data migrations.

    Args:
        wallet_id: ID of the wallet to recalculate
        create_snapshots: Whether to create balance history snapshots

    Returns:
        Dict with recalculation stats
    """
    logger.info(f"Starting balance recalculation for wallet_id={wallet_id}")
    start_time = datetime.now(UTC)

    try:
        db = get_async_db_instance()
        async with db.session() as session:
            session: AsyncSession
            balance_manager = BalanceManager(db=session, settings=settings)

            # Recalculate all balances
            balances = await balance_manager.recalculate_wallet_balances(
                wallet_id=wallet_id, create_snapshots=create_snapshots
            )

            # Commit changes
            await session.commit()

            duration = (datetime.now(UTC) - start_time).total_seconds()
            logger.info(f"Wallet {wallet_id} recalculation completed: {len(balances)} balances in {duration:.2f}s")

            return {
                "status": "success",
                "wallet_id": wallet_id,
                "balances_recalculated": len(balances),
                "snapshots_created": create_snapshots,
                "duration_seconds": duration,
            }

    except Exception as e:
        logger.error(f"Wallet recalculation failed for wallet_id={wallet_id}: {e}")
        logger.exception(e)
        return {"status": "error", "wallet_id": wallet_id, "error": str(e)}


@broker.task
async def recalculate_all_wallets(create_snapshots: bool = False) -> dict:
    """
    Recalculate balances for ALL wallets.

    WARNING: This is a very expensive operation! Only use for system-wide corrections.

    Args:
        create_snapshots: Whether to create balance history snapshots

    Returns:
        Dict with recalculation stats
    """
    logger.warning("Starting system-wide balance recalculation for ALL wallets")
    start_time = datetime.now(UTC)

    try:
        db = get_async_db_instance()
        async with db.session() as session:
            session: AsyncSession

            # Get all active wallets
            stmt = select(Wallet).where(Wallet.is_deleted == False)  # noqa: E712
            result = await session.execute(stmt)
            wallets = result.scalars().all()

            total_wallets = len(wallets)
            total_balances = 0
            failed_wallets = []

            for wallet in wallets:
                try:
                    balance_manager = BalanceManager(db=session, settings=settings)
                    balances = await balance_manager.recalculate_wallet_balances(
                        wallet_id=wallet.id, create_snapshots=create_snapshots
                    )
                    total_balances += len(balances)
                    await session.commit()
                    logger.info(f"Recalculated wallet {wallet.id}: {len(balances)} balances")

                except Exception as e:
                    logger.error(f"Failed to recalculate wallet {wallet.id}: {e}")
                    failed_wallets.append({"wallet_id": wallet.id, "error": str(e)})
                    await session.rollback()

            duration = (datetime.now(UTC) - start_time).total_seconds()
            logger.warning(
                f"System-wide recalculation completed: {total_wallets} wallets, "
                f"{total_balances} balances in {duration:.2f}s"
            )

            return {
                "status": "partial_success" if failed_wallets else "success",
                "wallets_processed": total_wallets,
                "balances_recalculated": total_balances,
                "failed_wallets": failed_wallets,
                "snapshots_created": create_snapshots,
                "duration_seconds": duration,
            }

    except Exception as e:
        logger.error(f"System-wide recalculation failed: {e}")
        logger.exception(e)
        return {"status": "error", "error": str(e)}


@broker.task(
    schedule=[{"cron": "0 3 * * *", "id": "cleanup_old_snapshots"}],
)
async def cleanup_old_snapshots() -> dict:
    """
    Clean up old balance history snapshots based on retention policies.

    Retention policy (from settings):
    - Hourly snapshots: Keep for `balance_hourly_retention_days` (default: 7 days)
    - Daily/Weekly/Monthly snapshots: Keep for `balance_history_retention_days` (default: 90 days)

    Returns:
        Dict with cleanup stats
    """
    logger.info("Starting balance history cleanup task")
    start_time = datetime.now(UTC)

    try:
        db = get_async_db_instance()
        async with db.session() as session:
            session: AsyncSession

            from backend.databases.models import BalanceHistory

            # Cleanup hourly snapshots older than retention period using bulk delete
            hourly_cutoff = datetime.now(UTC) - timedelta(days=settings.balance_hourly_retention_days)
            stmt = delete(BalanceHistory).where(
                BalanceHistory.snapshot_type == SnapshotType.HOURLY.value, BalanceHistory.snapshot_date < hourly_cutoff
            )
            result = await session.execute(stmt)
            hourly_deleted_count = getattr(result, "rowcount", 0) or 0

            # Cleanup daily/weekly/monthly snapshots older than retention period using bulk delete
            history_cutoff = datetime.now(UTC) - timedelta(days=settings.balance_history_retention_days)
            stmt = delete(BalanceHistory).where(
                BalanceHistory.snapshot_type.in_(
                    [SnapshotType.DAILY.value, SnapshotType.WEEKLY.value, SnapshotType.MONTHLY.value]
                ),
                BalanceHistory.snapshot_date < history_cutoff,
            )
            result = await session.execute(stmt)
            history_deleted_count = getattr(result, "rowcount", 0) or 0

            # Commit deletions
            await session.commit()

            total_deleted = hourly_deleted_count + history_deleted_count
            duration = (datetime.now(UTC) - start_time).total_seconds()

            logger.info(
                f"Cleanup completed: deleted {hourly_deleted_count} hourly + "
                f"{history_deleted_count} daily/weekly/monthly snapshots in {duration:.2f}s"
            )

            return {
                "status": "success",
                "hourly_deleted": hourly_deleted_count,
                "history_deleted": history_deleted_count,
                "total_deleted": total_deleted,
                "duration_seconds": duration,
            }

    except Exception as e:
        logger.error(f"Snapshot cleanup task failed: {e}")
        logger.exception(e)
        return {"status": "error", "error": str(e)}
