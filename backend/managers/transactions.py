from typing import TYPE_CHECKING

import sqlalchemy.exc
from fastapi import Depends

from backend import schemas
from backend.databases import get_db_session
from backend.databases.models import Transaction
from backend.errors import DatabaseError

if TYPE_CHECKING:
    from sqlalchemy.orm import Session as DBSession


class TransactionManager:
    def __init__(self, db: "DBSession" = Depends(get_db_session)) -> None:
        self.db = db

    def create_transaction(self, wallet_id: str, transaction_data: schemas.TransactionCreate) -> Transaction:
        new_transaction = Transaction(**transaction_data.model_dump(), wallet_id=wallet_id)
        self._transaction_save_or_raise(new_transaction)
        return new_transaction

    def _transaction_save_or_raise(self, transaction: Transaction) -> None:
        try:
            transaction.save(self.db)
        except sqlalchemy.exc.IntegrityError as e:
            if "duplicate key value" in str(e):
                pass
            else:
                raise DatabaseError(status_code=500, exception_message=f"Database integrity error: {str(e)}") from e
        except sqlalchemy.exc.SQLAlchemyError as e:
            raise DatabaseError(status_code=500, exception_message=f"Internal database error: {str(e)}") from e
        except Exception as e:
            raise DatabaseError(status_code=500, exception_message=f"Internal server error: {str(e)}") from e

    def get_transactions_by_wallet(self, wallet_id: str) -> list[Transaction]:
        return Transaction.get_many_by_kwargs(self.db, wallet_id=wallet_id)
