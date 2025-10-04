from backend import schemas
from backend.databases.models import Transaction, Wallet
from backend.errors import BadRequestException, DatabaseError
from backend.managers.base_crud import BaseCRUDManager
from backend.validators import get_uuid


class TransactionManager(BaseCRUDManager[Transaction]):
    """
    Best practice: never modify past transactions.
    If you need corrections, insert a reversing tx + new tx.
    All inserts must be idempotent (re-running job yields same result).
    Wrap updates in DB transactions.
    For corrections: recompute from earliest affected tx forward.
    """

    @property
    def _model_class(self) -> type[Transaction]:
        return Transaction

    def create_tx(self, transaction_data: schemas.TransactionCreateOrUpdate) -> Transaction:
        if (transaction_data.wallet_id and not transaction_data.cex_account_id) or (
            transaction_data.cex_account_id and not transaction_data.wallet_id
        ):
            return self.create(transaction_data)
        else:
            raise BadRequestException()

    def create_tx_for_wallet(self, wallet_id: str, transaction_data: schemas.TransactionCreateOrUpdate) -> Transaction:
        transaction = transaction_data.model_dump(exclude_unset=True)
        if wallet_uuid := get_uuid(wallet_id):
            wallet = Wallet.get_by_uuid(self.db, wallet_uuid)
            new_obj = self.model(**transaction, **{"wallet_id": wallet.id})
            new_obj.save(self.db)
            return new_obj
        raise DatabaseError(400, "Wallet does not exists")
