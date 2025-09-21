from fastapi import APIRouter, Depends

from backend.managers import TransactionManager
from backend.schemas import Transaction, TransactionCreate

router = APIRouter()


@router.post("/transaction/{wallet_id}", response_model=Transaction)
def create_transaction(
        wallet_id: str,
        transaction_data: TransactionCreate,
        transaction_manager: TransactionManager = Depends()
):
    return Transaction.model_validate(
        transaction_manager.create_transaction(wallet_id, transaction_data).to_schema()
    )

@router.get("/transaction/{wallet_id}", response_model=list[Transaction])
def get_transactions(
        wallet_id: str,
        transaction_manager: TransactionManager = Depends()
):
    return transaction_manager.get_transactions_by_wallet(wallet_id)
