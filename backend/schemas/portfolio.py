from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from backend.schemas import WalletResponse


class PortfolioBase(BaseModel):
    name: str = "Portfolio 1"
    memo: str | None = None

    model_config = ConfigDict(from_attributes=True)


class Portfolio(PortfolioBase):
    uuid: UUID
    created_at: datetime
    wallets: list[WalletResponse] = []


class PortfolioCreateOrUpdate(PortfolioBase):
    pass


class PortfolioCreateOrUpdateResponse(PortfolioBase):
    uuid: UUID
    created_at: datetime


class PortfolioPatch(BaseModel):
    name: str | None = None
    memo: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PortfolioAll(BaseModel):
    portfolios: list[Portfolio] = []

    model_config = ConfigDict(from_attributes=True)
