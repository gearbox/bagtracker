"""
Balance API Endpoints
FastAPI router for balance operations.
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from backend.managers import BalanceHistoryManager, BalanceManager
from backend.schemas import (
    BalanceHistoryPoint,
    BalanceResponse,
    PortfolioChartResponse,
    SnapshotType,
    WalletBalancesResponse,
)

router = APIRouter(prefix="/balance")


@router.get("/wallet/{wallet_uuid}", response_model=WalletBalancesResponse)
async def get_wallet_balances(
    balance_manager: Annotated[BalanceManager, Depends(BalanceManager)],
    wallet_uuid: str,
    include_zero: bool = Query(False, description="Include zero balances"),
):
    """
    Get all balances for a wallet.

    - **wallet_uuid**: Wallet UUID
    - **include_zero**: Include tokens with zero balance
    """
    balances = await balance_manager.get_wallet_balances(wallet_uuid=UUID(wallet_uuid), include_zero=include_zero)

    # Get wallet totals
    if balances:
        wallet_id = balances[0].wallet_id
        totals = await balance_manager.get_wallet_total_value(wallet_id)
    else:
        zero_value_decimal = Decimal(0)
        totals = {
            "total_value_usd": zero_value_decimal,
            "total_unrealized_pnl_usd": zero_value_decimal,
            "token_count": 0,
        }

    return WalletBalancesResponse(
        wallet_id=balances[0].wallet_id if balances else 0,
        balances=[BalanceResponse.model_validate(b) for b in balances],
        **totals,
    )


@router.get("/history/token/{wallet_id}/{token_id}/{chain_id}", response_model=list[BalanceHistoryPoint])
async def get_token_balance_history(
    history_manager: Annotated[BalanceHistoryManager, Depends(BalanceHistoryManager)],
    wallet_id: int,
    token_id: int,
    chain_id: int,
    start_date: datetime | None = Query(None, description="Start date filter"),
    end_date: datetime | None = Query(None, description="End date filter"),
    snapshot_type: SnapshotType | None = Query(None, description="Snapshot type filter"),
):
    """
    Get balance history for a specific token.
    Perfect for individual token charts.

    - **wallet_id**: Wallet ID
    - **token_id**: Token ID
    - **chain_id**: Chain ID
    - **start_date**: Optional start date
    - **end_date**: Optional end date
    - **snapshot_type**: Filter by type (transaction, hourly, daily, weekly, monthly)
    """
    history = await history_manager.get_balance_history(
        wallet_id=wallet_id,
        token_id=token_id,
        chain_id=chain_id,
        start_date=start_date,
        end_date=end_date,
        snapshot_type=snapshot_type,
    )

    return [BalanceHistoryPoint.model_validate(h) for h in history]


@router.get("/history/portfolio/{wallet_id}", response_model=PortfolioChartResponse)
async def get_portfolio_history(
    wallet_id: int,
    history_manager: Annotated[BalanceHistoryManager, Depends(BalanceHistoryManager)],
    start_date: datetime | None = Query(None, description="Start date filter"),
    end_date: datetime | None = Query(None, description="End date filter"),
    snapshot_type: SnapshotType = Query(SnapshotType.DAILY, description="Snapshot type"),
):
    """
    Get aggregated portfolio value over time.
    Perfect for portfolio overview charts.

    - **wallet_id**: Wallet ID
    - **start_date**: Optional start date
    - **end_date**: Optional end date
    - **snapshot_type**: Aggregation level (HOURLY, DAILY, WEEKLY, MONTHLY)
    """
    history = await history_manager.get_portfolio_history_aggregated(
        wallet_id=wallet_id, start_date=start_date, end_date=end_date, snapshot_type=snapshot_type
    )

    return PortfolioChartResponse(history=history)


@router.post("/recalculate/wallet/{wallet_id}", response_model=dict)
async def recalculate_wallet_balances(
    wallet_id: int,
    balance_manager: Annotated[BalanceManager, Depends(BalanceManager)],
    create_snapshots: bool = Query(True, description="Create history snapshots"),
):
    """
    Recalculate all balances for a wallet from scratch.

    ⚠️ WARNING: This is an expensive operation!

    Use cases:
    - After data migration
    - To fix inconsistencies
    - After bulk transaction imports

    - **wallet_id**: Wallet ID to recalculate
    - **create_snapshots**: Whether to create history snapshots
    """
    balances = await balance_manager.recalculate_wallet_balances(wallet_id=wallet_id, create_snapshots=create_snapshots)

    return {"wallet_id": wallet_id, "recalculated_tokens": len(balances), "status": "success"}


@router.post("/update-prices/{token_id}", response_model=dict)
async def update_token_price(
    token_id: int,
    balance_manager: Annotated[BalanceManager, Depends(BalanceManager)],
    price_usd: Decimal = Query(..., description="New price in USD"),
    snapshot_type: SnapshotType = Query(SnapshotType.HOURLY, description="Snapshot type"),
    create_snapshots: bool = Query(True, description="Create history snapshots"),
):
    """
    Update price for all balances of a specific token.
    Used for price feeds integration.

    - **token_id**: Token ID
    - **price_usd**: New price in USD
    - **snapshot_type**: Type of snapshot to create (default: HOURLY)
    - **create_snapshots**: Whether to create history snapshots
    """
    balances = await balance_manager.update_prices(
        token_id=token_id, new_price_usd=price_usd, snapshot_type=snapshot_type, create_snapshots=create_snapshots
    )

    return {"token_id": token_id, "price_usd": price_usd, "balances_updated": len(balances), "status": "success"}
