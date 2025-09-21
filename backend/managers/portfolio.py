from typing import TYPE_CHECKING

from fastapi import Depends

from backend.databases import get_db_session
from backend.databases.models import Portfolio
from backend.managers.base_crud import BaseCRUDManager

if TYPE_CHECKING:
    from sqlalchemy.orm import Session as DBSession


class PortfolioManager(BaseCRUDManager):
    def __init__(self, db: "DBSession" = Depends(get_db_session)) -> None:
        super().__init__(db)

    def _get_db_model(self) -> type[Portfolio]:
        return Portfolio
