from backend.databases.models import Wallet
from backend.errors import WalletError
from backend.managers.base_crud import BaseCRUDManager


class WalletManager(BaseCRUDManager[Wallet]):
    @property
    def _model_class(self) -> type[Wallet]:
        return Wallet

    def get_by_address(self, address: str) -> Wallet:
        if wallet := self.db.query(self._model_class).filter_by(address=address).one_or_none():
            return wallet
        raise WalletError()
