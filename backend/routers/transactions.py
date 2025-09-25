from typing import Annotated

from fastapi import APIRouter, Depends

from backend.managers import TransactionManager
from backend.schemas import Transaction, TransactionCreateOrUpdate, TransactionPatch, TransactionsAll

router = APIRouter()


@router.post("/transaction/", response_model=Transaction)
def create_transaction(
    transaction_data: TransactionCreateOrUpdate,
    transaction_manager: Annotated[TransactionManager, Depends(TransactionManager)],
) -> Transaction:
    return Transaction.model_validate(transaction_manager.create_tx(transaction_data))


@router.post("/transaction/wallet/{wallet_id}", response_model=Transaction)
def create_wallet_transaction(
    wallet_id: str,
    transaction_data: TransactionCreateOrUpdate,
    transaction_manager: Annotated[TransactionManager, Depends(TransactionManager)],
) -> Transaction:
    return Transaction.model_validate(transaction_manager.create_tx_for_wallet(wallet_id, transaction_data))


@router.get("/wallet/transactions/{wallet_id}", response_model=TransactionsAll, tags=["Wallets"])
def get_transactions_by_wallet_id(
    wallet_id: str,
    transaction_manager: Annotated[TransactionManager, Depends(TransactionManager)],
) -> TransactionsAll:
    return TransactionsAll.model_validate({"transactions": transaction_manager.get_all_by_kwargs(wallet_id=wallet_id)})


@router.get("/cex/transactions/{cex_account_id}", response_model=TransactionsAll, tags=["CEX"])
def get_transactions_by_cex_account_id(
    cex_account_id: str,
    transaction_manager: Annotated[TransactionManager, Depends(TransactionManager)],
) -> TransactionsAll:
    return TransactionsAll.model_validate(
        {"transactions": transaction_manager.get_all_by_kwargs(cex_account_id=cex_account_id)}
    )


@router.get("/transaction/{transaction_id}", response_model=Transaction)
def get_transaction(
    transaction_id: str,
    transaction_manager: Annotated[TransactionManager, Depends(TransactionManager)],
) -> Transaction:
    return Transaction.model_validate(transaction_manager.get(transaction_id))


@router.put("/transaction/{transaction_id}", response_model=Transaction)
def update_wallet_transaction(
    transaction_id: str,
    transaction_data: TransactionCreateOrUpdate,
    transaction_manager: Annotated[TransactionManager, Depends(TransactionManager)],
) -> Transaction:
    return Transaction.model_validate(transaction_manager.update(transaction_id, transaction_data))


@router.patch("/transaction/{transaction_id}", response_model=Transaction)
def patch_transaction(
    transaction_id: str,
    transaction_data: TransactionPatch,
    transaction_manager: Annotated[TransactionManager, Depends(TransactionManager)],
) -> Transaction:
    return Transaction.model_validate(transaction_manager.patch(transaction_id, transaction_data))


@router.delete("/transaction/{transaction_id}", response_model=None, status_code=204)
def delete_transaction(
    transaction_id: str,
    transaction_manager: Annotated[TransactionManager, Depends(TransactionManager)],
) -> Transaction:
    return Transaction.model_validate(transaction_manager.delete(transaction_id))
