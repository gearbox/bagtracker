from typing import Annotated

from fastapi import APIRouter, Depends

from backend.managers import TransactionManager
from backend.schemas import Transaction, TransactionCreateOrUpdate, TransactionPatch, TransactionsAll

router = APIRouter()


@router.post("/transaction/", response_model=Transaction)
async def create_transaction(
    transaction_data: TransactionCreateOrUpdate,
    transaction_manager: Annotated[TransactionManager, Depends(TransactionManager)],
) -> Transaction:
    return Transaction.model_validate(await transaction_manager.create_tx(transaction_data))


@router.get("/wallet/transactions/{wallet_uuid}", response_model=TransactionsAll, tags=["Wallets"])
async def get_transactions_by_wallet_uuid(
    wallet_uuid: str,
    transaction_manager: Annotated[TransactionManager, Depends(TransactionManager)],
) -> TransactionsAll:
    return TransactionsAll.model_validate(
        {"transactions": await transaction_manager.get_by_wallet_uuid(wallet_uuid=wallet_uuid)}
    )


@router.get("/cex/transactions/{cex_account_id}", response_model=TransactionsAll, tags=["CEX"])
async def get_transactions_by_cex_account_id(
    cex_account_id: str,
    transaction_manager: Annotated[TransactionManager, Depends(TransactionManager)],
) -> TransactionsAll:
    return TransactionsAll.model_validate(
        {"transactions": await transaction_manager.get_all(cex_account_id=cex_account_id)}
    )


@router.get("/transaction/{transaction_id}", response_model=Transaction)
async def get_transaction(
    transaction_id: str,
    transaction_manager: Annotated[TransactionManager, Depends(TransactionManager)],
) -> Transaction:
    return Transaction.model_validate(await transaction_manager.get(transaction_id))


@router.put("/transaction/{transaction_id}", response_model=Transaction)
async def update_wallet_transaction(
    transaction_id: str,
    recalculate: bool,
    transaction_data: TransactionCreateOrUpdate,
    transaction_manager: Annotated[TransactionManager, Depends(TransactionManager)],
) -> Transaction:
    return Transaction.model_validate(
        await transaction_manager.update_tx(transaction_id, transaction_data, recalculate)
    )


@router.patch("/transaction/{transaction_id}", response_model=Transaction)
async def patch_transaction(
    transaction_id: str,
    transaction_data: TransactionPatch,
    transaction_manager: Annotated[TransactionManager, Depends(TransactionManager)],
) -> Transaction:
    return Transaction.model_validate(await transaction_manager.patch(transaction_id, transaction_data))


@router.delete("/transaction/{transaction_id}", response_model=None, status_code=204)
async def delete_transaction(
    transaction_id: str,
    transaction_manager: Annotated[TransactionManager, Depends(TransactionManager)],
) -> None:
    await transaction_manager.delete_tx(transaction_id)


@router.post("/transaction/{transaction_id}", response_model=Transaction)
async def mark_cancelled(
    transaction_id: str,
    transaction_manager: Annotated[TransactionManager, Depends(TransactionManager)],
) -> Transaction:
    return Transaction.model_validate(await transaction_manager.mark_as_cancelled(transaction_id))
