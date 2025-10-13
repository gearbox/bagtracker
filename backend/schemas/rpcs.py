import uuid
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict


class RpcBase(BaseModel):
    chain_id: int
    name: str
    rpc_url: str | None = None  # optional: e.g. "mainnet.infura.io"
    is_failover_url: bool = False
    priority: int = 0  # Lower = higher priority
    is_active: bool = True
    memo: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RpcCreateOrUpdate(RpcBase):
    pass


class Rpc(RpcBase):
    uuid: uuid.UUID


class RpcPatch(BaseModel):
    chain_id: int | None = None
    name: str | None = None
    rpc_url: str | None = None
    is_failover_url: bool | None = None
    priority: int | None = None
    is_active: bool | None = None
    memo: str | None = None


class RpcAll(BaseModel):
    rpcs: Sequence[Rpc]
