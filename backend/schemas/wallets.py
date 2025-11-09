from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from backend.schemas import WalletAddressCreate, WalletAddressResponse, WalletAddressWithChain


class WalletType(Enum):
    METAMASK = "metamask"
    TRONLINK = "tronlink"
    LEATHER = "leather"


class WalletBase(BaseModel):
    name: str | None = None
    wallet_type: WalletType = WalletType.METAMASK
    memo: str | None = None

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)


class WalletCreateMultichain(WalletBase):
    """
    Create a new multichain wallet.
    Provide one or more chain addresses.
    """

    addresses: list[WalletAddressCreate]

    @field_validator("addresses")
    @classmethod
    def validate_addresses(cls, v: list) -> list:
        if not v:
            raise ValueError("At least one address is required")
        return v


class WalletCreateOrUpdate(WalletBase):
    chain_id: int = 1  # Default to Ethereum Mainnet


class WalletAddChain(BaseModel):
    """Add a new chain to existing wallet."""

    chain_id: int
    address: str
    derivation_path: str | None = None


class WalletResponse(WalletBase):
    """Wallet response with all addresses."""

    uuid: UUID
    created_at: datetime
    last_sync_at: datetime | None
    total_value_usd: Decimal
    addresses: list[WalletAddressWithChain]

    model_config = ConfigDict(from_attributes=True)

    @property
    def chain_count(self) -> int:
        """Number of chains this wallet is active on."""
        return len([addr for addr in self.addresses if addr.is_active])


class WalletListResponse(BaseModel):
    """Simplified wallet response for lists."""

    uuid: UUID
    name: str | None
    wallet_type: str
    total_value_usd: Decimal
    chain_count: int
    addresses: list[WalletAddressResponse]
    created_at: datetime


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
    last_sync_at: datetime | None = None
    total_value_usd: Decimal
    # transactions: list[Transaction] = []


class WalletAll(BaseModel):
    wallets: Sequence[WalletResponse] = []
