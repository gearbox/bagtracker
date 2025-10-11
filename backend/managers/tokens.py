from backend.databases.models import Token
from backend.managers.base_crud import BaseCRUDManager


class TokenManager(BaseCRUDManager):
    @property
    def _model_class(self) -> type[Token]:
        return Token
