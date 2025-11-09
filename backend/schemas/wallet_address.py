from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from backend.schemas import Chain


class WalletAddressBase(BaseModel):
    """Base schema for wallet address."""

    address: str
    chain_id: int
    derivation_path: str | None = None
    is_active: bool = True

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        """Basic address validation."""
        if not v or not v.strip():
            raise ValueError("Address cannot be empty")
        return v.strip()


class WalletAddressCreate(WalletAddressBase):
    """Schema for creating new wallet address."""

    pass


class WalletAddressUpdate(BaseModel):
    """Schema for updating wallet address."""

    is_active: bool | None = None
    derivation_path: str | None = None


class WalletAddressResponse(WalletAddressBase):
    """Response schema for wallet address."""

    uuid: UUID
    wallet_id: int
    address_lowercase: str
    last_sync_at: datetime | None
    last_sync_block: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WalletAddressWithChain(WalletAddressResponse):
    """Wallet address with chain details."""

    chain: "Chain"

    model_config = ConfigDict(from_attributes=True)
