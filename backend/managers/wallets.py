from backend.databases.models import Wallet
from backend.managers.base_crud import BaseCRUDManager


class WalletManager(BaseCRUDManager[Wallet]):
    # TODO: Soft delete does not work, need to fix it
    @property
    def _model_class(self) -> type[Wallet]:
        return Wallet

    async def get_by_address(self, address: str) -> Wallet:
        return await Wallet.get_one(self.db, address=address)
