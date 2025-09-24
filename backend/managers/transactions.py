from backend import schemas
from backend.databases.models import Transaction
from backend.errors import BadRequestException
from backend.managers.base_crud import BaseCRUDManager


class TransactionManager(BaseCRUDManager[Transaction]):
    @property
    def _model_class(self) -> type[Transaction]:
        return Transaction

    def create_transaction(self, transaction_data: schemas.TransactionCreateOrUpdate) -> Transaction:
        if (transaction_data.wallet_id and not transaction_data.cex_account_id) or (
            transaction_data.cex_account_id and not transaction_data.wallet_id
        ):
            new_transaction = Transaction(**transaction_data.model_dump())
        else:
            raise BadRequestException()
        self._save_or_raise(new_transaction)
        return new_transaction
