"""
Background tasks for balance snapshots and transaction processing.

This module defines Taskiq tasks for periodic operations:
- Balance snapshot creation (hourly, daily, weekly, monthly)
- Transaction recalculation
- Price updates with snapshots
"""

from datetime import UTC, datetime, timedelta

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.databases.factory_async import get_async_db_instance
from backend.databases.models import Balance, Wallet
from backend.managers.balance import BalanceManager
from backend.schemas import SnapshotType
from backend.services.balance_calculator import BalanceCalculator
from backend.settings import get_settings
from backend.taskiq_broker import broker

settings = get_settings()


@broker.task(
    schedule=[{"cron": "5 * * * *", "id": "hourly_balance_snapshots"}],
)
async def create_hourly_snapshots() -> dict:
    """
    Create hourly balance snapshots for all active balances.

    This task runs every hour and creates snapshots of all non-zero balances.
    Snapshots are stored in the balance_history TimescaleDB hypertable.

    Returns:
        Dict with task execution stats
    """
    if not settings.balance_snapshot_enabled or not settings.balance_hourly_snapshots:
        logger.info("Hourly snapshots disabled in settings")
        return {"status": "skipped", "reason": "disabled_in_settings"}

    logger.info("Starting hourly balance snapshots task")
    start_time = datetime.now(UTC)

    try:
        db = get_async_db_instance()
        async with db.session() as session:
            session: AsyncSession
            calculator = BalanceCalculator(db=session, settings=settings)

            # Get all non-zero balances
            stmt = select(Balance).where(Balance.amount_decimal > 0)
            result = await session.execute(stmt)
            balances = result.scalars().all()

            snapshot_count = 0
            for balance in balances:
                await calculator._create_history_snapshot(
                    balance=balance, snapshot_type=SnapshotType.HOURLY, triggered_by="scheduled_hourly"
                )
                snapshot_count += 1

            # Commit all snapshots
            await session.commit()

            duration = (datetime.now(UTC) - start_time).total_seconds()
            logger.info(f"Hourly snapshots completed: {snapshot_count} snapshots in {duration:.2f}s")

            return {
                "status": "success",
                "snapshot_type": "hourly",
                "snapshots_created": snapshot_count,
                "duration_seconds": duration,
            }

    except Exception as e:
        logger.error(f"Hourly snapshot task failed: {e}")
        logger.exception(e)
        return {"status": "error", "error": str(e)}


@broker.task(
    schedule=[{"cron": "15 0 * * *", "id": "daily_balance_snapshots"}],
)
async def create_daily_snapshots() -> dict:
    """
    Create daily balance snapshots for all active balances.

    This task runs once per day and creates snapshots of all non-zero balances.

    Returns:
        Dict with task execution stats
    """
    if not settings.balance_snapshot_enabled or not settings.balance_daily_snapshots:
        logger.info("Daily snapshots disabled in settings")
        return {"status": "skipped", "reason": "disabled_in_settings"}

    logger.info("Starting daily balance snapshots task")
    start_time = datetime.now(UTC)

    try:
        db = get_async_db_instance()
        async with db.session() as session:
            session: AsyncSession
            calculator = BalanceCalculator(db=session, settings=settings)

            # Get all non-zero balances
            stmt = select(Balance).where(Balance.amount_decimal > 0)
            result = await session.execute(stmt)
            balances = result.scalars().all()

            snapshot_count = 0
            for balance in balances:
                await calculator._create_history_snapshot(
                    balance=balance, snapshot_type=SnapshotType.DAILY, triggered_by="scheduled_daily"
                )
                snapshot_count += 1

            # Commit all snapshots
            await session.commit()

            duration = (datetime.now(UTC) - start_time).total_seconds()
            logger.info(f"Daily snapshots completed: {snapshot_count} snapshots in {duration:.2f}s")

            return {
                "status": "success",
                "snapshot_type": "daily",
                "snapshots_created": snapshot_count,
                "duration_seconds": duration,
            }

    except Exception as e:
        logger.error(f"Daily snapshot task failed: {e}")
        logger.exception(e)
        return {"status": "error", "error": str(e)}


@broker.task(
    schedule=[{"cron": "0 1 * * 0", "id": "weekly_balance_snapshots"}],
)
async def create_weekly_snapshots() -> dict:
    """
    Create weekly balance snapshots for all active balances.

    This task runs once per week and creates snapshots of all non-zero balances.

    Returns:
        Dict with task execution stats
    """
    if not settings.balance_snapshot_enabled:
        logger.info("Weekly snapshots disabled in settings")
        return {"status": "skipped", "reason": "disabled_in_settings"}

    logger.info("Starting weekly balance snapshots task")
    start_time = datetime.now(UTC)

    try:
        db = get_async_db_instance()
        async with db.session() as session:
            session: AsyncSession
            calculator = BalanceCalculator(db=session, settings=settings)

            # Get all non-zero balances
            stmt = select(Balance).where(Balance.amount_decimal > 0)
            result = await session.execute(stmt)
            balances = result.scalars().all()

            snapshot_count = 0
            for balance in balances:
                await calculator._create_history_snapshot(
                    balance=balance, snapshot_type=SnapshotType.WEEKLY, triggered_by="scheduled_weekly"
                )
                snapshot_count += 1

            # Commit all snapshots
            await session.commit()

            duration = (datetime.now(UTC) - start_time).total_seconds()
            logger.info(f"Weekly snapshots completed: {snapshot_count} snapshots in {duration:.2f}s")

            return {
                "status": "success",
                "snapshot_type": "weekly",
                "snapshots_created": snapshot_count,
                "duration_seconds": duration,
            }

    except Exception as e:
        logger.error(f"Weekly snapshot task failed: {e}")
        logger.exception(e)
        return {"status": "error", "error": str(e)}


@broker.task(
    schedule=[{"cron": "0 2 1 * *", "id": "monthly_balance_snapshots"}],
)
async def create_monthly_snapshots() -> dict:
    """
    Create monthly balance snapshots for all active balances.

    This task runs once per month and creates snapshots of all non-zero balances.

    Returns:
        Dict with task execution stats
    """
    if not settings.balance_snapshot_enabled:
        logger.info("Monthly snapshots disabled in settings")
        return {"status": "skipped", "reason": "disabled_in_settings"}

    logger.info("Starting monthly balance snapshots task")
    start_time = datetime.now(UTC)

    try:
        db = get_async_db_instance()
        async with db.session() as session:
            session: AsyncSession
            calculator = BalanceCalculator(db=session, settings=settings)

            # Get all non-zero balances
            stmt = select(Balance).where(Balance.amount_decimal > 0)
            result = await session.execute(stmt)
            balances = result.scalars().all()

            snapshot_count = 0
            for balance in balances:
                await calculator._create_history_snapshot(
                    balance=balance, snapshot_type=SnapshotType.MONTHLY, triggered_by="scheduled_monthly"
                )
                snapshot_count += 1

            # Commit all snapshots
            await session.commit()

            duration = (datetime.now(UTC) - start_time).total_seconds()
            logger.info(f"Monthly snapshots completed: {snapshot_count} snapshots in {duration:.2f}s")

            return {
                "status": "success",
                "snapshot_type": "monthly",
                "snapshots_created": snapshot_count,
                "duration_seconds": duration,
            }

    except Exception as e:
        logger.error(f"Monthly snapshot task failed: {e}")
        logger.exception(e)
        return {"status": "error", "error": str(e)}


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

            # Cleanup hourly snapshots older than retention period
            hourly_cutoff = datetime.now(UTC) - timedelta(days=settings.balance_hourly_retention_days)
            stmt = select(BalanceHistory).where(
                BalanceHistory.snapshot_type == SnapshotType.HOURLY.value, BalanceHistory.snapshot_date < hourly_cutoff
            )
            result = await session.execute(stmt)
            hourly_to_delete = result.scalars().all()

            for snapshot in hourly_to_delete:
                await session.delete(snapshot)

            hourly_deleted_count = len(hourly_to_delete)

            # Cleanup daily/weekly/monthly snapshots older than retention period
            history_cutoff = datetime.now(UTC) - timedelta(days=settings.balance_history_retention_days)
            stmt = select(BalanceHistory).where(
                BalanceHistory.snapshot_type.in_(
                    [SnapshotType.DAILY.value, SnapshotType.WEEKLY.value, SnapshotType.MONTHLY.value]
                ),
                BalanceHistory.snapshot_date < history_cutoff,
            )
            result = await session.execute(stmt)
            history_to_delete = result.scalars().all()

            for snapshot in history_to_delete:
                await session.delete(snapshot)

            history_deleted_count = len(history_to_delete)

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
