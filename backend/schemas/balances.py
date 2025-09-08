from datetime import datetime

from pydantic import BaseModel


class Balance(BaseModel):
    contract_address: str | None
    symbol: str
    name: str
    amount: str
    type: str
    fetched_at: datetime

    class Config:
        from_attributes = True
