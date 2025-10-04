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


# class EnhancedBalanceSchema(APIBaseModel):
#     """Enhanced balance schema with proper decimal handling"""
#     id: UUID
#     wallet_id: UUID
#     symbol: str
#     name: Optional[str]
#     balance_decimal: Decimal
#     value_usd: Decimal
#     price_usd: Optional[Decimal] = None
#     created_at: datetime
#     updated_at: datetime

#     # Add computed display fields
#     @property
#     def balance_display(self) -> str:
#         return f"{self.balance_decimal} {self.symbol}"

#     @property
#     def value_usd_display(self) -> str:
#         return f"${self.value_usd:,.2f}"
