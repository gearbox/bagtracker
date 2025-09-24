from backend.databases.models import Chain
from backend.managers.base_crud import BaseCRUDManager


class ChainManager(BaseCRUDManager):
    @property
    def _model_class(self) -> type[Chain]:
        return Chain
