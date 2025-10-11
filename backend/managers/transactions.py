from backend import schemas
from backend.databases.models import CexAccount, Transaction, Wallet
from backend.errors import BadRequestException
from backend.managers.base_crud import BaseCRUDManager
from backend.validators import get_uuid_or_rise


class TransactionManager(BaseCRUDManager[Transaction]):
    """
    Best practice: never modify past transactions.
    If you need corrections, insert a reversing tx + new tx.
    All inserts must be idempotent (re-running job yields same result).
    Wrap updates in DB transactions.
    For corrections: recompute from earliest affected tx forward.
    """

    # Define relationships to eager load
    eager_load = []

    @property
    def _model_class(self) -> type[Transaction]:
        return Transaction

    async def create_tx(self, transaction_data: schemas.TransactionCreateOrUpdate) -> Transaction:
        transaction = transaction_data.model_dump(exclude_unset=True)
        if transaction_data.wallet_uuid and not transaction_data.cex_account_uuid:
            wallet = await Wallet.get_by_uuid(self.db, transaction_data.wallet_uuid)
            transaction["wallet_id"] = wallet.id
        elif transaction_data.cex_account_uuid and not transaction_data.wallet_uuid:
            cex_account = await CexAccount.get_by_uuid(self.db, transaction_data.cex_account_uuid)
            transaction["cex_account_id"] = cex_account.id
        else:
            raise BadRequestException()
        return await self.create(transaction)

    # async def create_tx_for_wallet(
    #     self, wallet_id: str, transaction_data: schemas.TransactionCreateOrUpdate
    # ) -> Transaction:
    #     transaction = transaction_data.model_dump(exclude_unset=True)
    #     try:
    #         wallet = await Wallet.get_by_uuid(self.db, get_uuid_or_rise(wallet_id))
    #     except ValueError as e:
    #         raise BadRequestException("Wallet does not exists") from e
    #     transaction[wallet_id] = wallet.id
    #     # TODO: Should we use self.create instead?
    #     new_obj = self.model()
    #     return await new_obj.create(self.db, transaction)

    async def get_by_wallet_uuid(self, wallet_uuid: str):
        wallet = await Wallet.get_by_uuid(self.db, get_uuid_or_rise(wallet_uuid))
        return await self.get_all(wallet_id=wallet.id)
