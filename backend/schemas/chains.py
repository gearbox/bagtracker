from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ChainType(StrEnum):
    EVM = "evm"
    NONEVM = "non-evm"


class BaseChain(BaseModel):
    name: str
    name_full: str | None = None
    chain_type: ChainType
    chain_id: int | None = None
    explorer_url: str | None = None

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)


class Chain(BaseChain):
    id: int


class ChainCreateOrUpdate(BaseChain):
    id: int | None = None


class ChainPatch(BaseModel):
    id: int | None = None
    name: str | None = None
    name_full: str | None = None
    chain_type: ChainType | None = None
    chain_id: int | None = None
    explorer_url: str | None = None

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)
