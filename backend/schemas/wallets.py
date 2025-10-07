from collections.abc import Sequence
from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from backend.schemas import Chain


class WalletType(Enum):
    METAMASK = "metamask"
    TRONLINK = "tronlink"
    LEATHER = "leather"


class WalletBase(BaseModel):
    name: str | None = None
    wallet_type: WalletType = WalletType.METAMASK
    address: str
    memo: str | None = None

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)


class WalletCreateOrUpdate(WalletBase):
    chain_id: int = 1  # Default to Ethereum Mainnet


class WalletPatch(BaseModel):
    name: str | None = None
    wallet_type: WalletType | None = None
    address: str | None = None
    memo: str | None = None
    chain_id: int | None = None

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)


class Wallet(WalletBase):
    uuid: UUID
    created_at: datetime
    chain: Chain | None = None
    # transactions: list[Transaction] = []


class WalletAll(BaseModel):
    wallets: Sequence[Wallet] = []
