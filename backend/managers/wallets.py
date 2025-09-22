from backend.databases.models import Wallet
from backend.managers.base_crud import BaseCRUDManager


class WalletManager(BaseCRUDManager):

    @property
    def _model_class(self) -> type[Wallet]:
        return Wallet
