from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.schemas import Wallet


class PortfolioBase(BaseModel):
    name: str
    memo: str | None = None
    wallets: list[Wallet] = []

    model_config = ConfigDict(from_attributes=True)


class Portfolio(PortfolioBase):
    id: str
    created_at: datetime
