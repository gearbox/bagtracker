from backend.databases.models import BalanceHistory
from backend.managers.base_crud import BaseCRUDManager


class WalletManager(BaseCRUDManager[BalanceHistory]):
    @property
    def _model_class(self) -> type[BalanceHistory]:
        return BalanceHistory
