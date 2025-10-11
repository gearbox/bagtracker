from collections.abc import Sequence
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class BaseToken(BaseModel):
    chain_id: int
    symbol: str
    name: str | None = None
    decimals: int
    contract_address: str | None = None
    contract_address_lowercase: str | None = None
    token_standard: str | None = None  # TODO: Use Enum for all standards
    is_native: bool = False

    coingecko_id: str | None = None
    coinmarketcap_id: int | None = None
    current_price_usd: Decimal | None = Decimal("0.00")
    market_cap_usd: Decimal | None = Decimal("0.00")
    volume_24h_usd: Decimal | None = Decimal("0.00")
    price_change_24h_percent: Decimal | None = Decimal("0.00")

    # Metadata
    logo_url: str | None = None
    description: str | None = None
    project_url: str | None = None
    whitepaper_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TokenCreateOrUpdate(BaseToken):
    pass


class Token(BaseToken):
    id: int


class TokenAll(BaseModel):
    tokens: Sequence[Token]


class TokenPatch(BaseModel):
    chain_id: int | None = None
    symbol: str | None = None
    name: str | None = None
    decimals: int | None = None
    contract_address: str | None = None
    contract_address_lowercase: str | None = None
    token_standard: str | None = None
    is_native: bool = False

    coingecko_id: str | None = None
    coinmarketcap_id: int | None = None
    current_price_usd: Decimal | None = Decimal("0.00")
    market_cap_usd: Decimal | None = Decimal("0.00")
    volume_24h_usd: Decimal | None = Decimal("0.00")
    price_change_24h_percent: Decimal | None = Decimal("0.00")

    # Metadata
    logo_url: str | None = None
    description: str | None = None
    project_url: str | None = None
    whitepaper_url: str | None = None

    model_config = ConfigDict(from_attributes=True)
