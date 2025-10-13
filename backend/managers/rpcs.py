from backend.databases.models import RPC
from backend.managers.base_crud import BaseCRUDManager


class RpcManager(BaseCRUDManager):
    # Define relationships to eager load
    eager_load = []

    @property
    def _model_class(self) -> type[RPC]:
        return RPC
