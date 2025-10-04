from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from backend.schemas import Wallet


class PortfolioBase(BaseModel):
    name: str = "Portfolio 1"
    memo: str | None = None

    model_config = ConfigDict(from_attributes=True)


class Portfolio(PortfolioBase):
    uuid: UUID
    created_at: datetime
    wallets: list[Wallet] = []


class PortfolioCreateOrUpdate(PortfolioBase):
    pass


class PortfolioPatch(BaseModel):
    name: str | None = None
    memo: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PortfolioAll(BaseModel):
    portfolios: list[Portfolio] = []

    model_config = ConfigDict(from_attributes=True)
