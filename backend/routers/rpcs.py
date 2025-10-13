from typing import Annotated

from fastapi import APIRouter, Depends

from backend.managers import RpcManager
from backend.schemas import Rpc, RpcAll, RpcCreateOrUpdate, RpcPatch

router = APIRouter()


@router.post("/rpcs/", response_model=Rpc)
async def create_rpc(
    rpc_data: RpcCreateOrUpdate,
    rpc_manager: Annotated[RpcManager, Depends(RpcManager)],
) -> Rpc:
    await rpc_manager.sync_sequence()
    return Rpc.model_validate(await rpc_manager.create_from_schema(rpc_data))


@router.get("/rpcs/", response_model=RpcAll)
async def list_rpcs(
    rpc_manager: Annotated[RpcManager, Depends(RpcManager)],
) -> RpcAll:
    return RpcAll(rpcs=await rpc_manager.get_all())


@router.get("/rpcs/{rpc_id}", response_model=Rpc)
async def get_rpc(rpc_id: int | str, rpc_manager: Annotated[RpcManager, Depends(RpcManager)]) -> Rpc:
    return Rpc.model_validate(await rpc_manager.get(rpc_id))


@router.put("/rpcs/{rpc_id}", response_model=Rpc)
async def update_rpc(
    rpc_id: str,
    rpc_data: RpcCreateOrUpdate,
    rpc_manager: Annotated[RpcManager, Depends(RpcManager)],
) -> Rpc:
    return Rpc.model_validate(await rpc_manager.update(rpc_id, rpc_data))


@router.patch("/rpcs/{rpc_id}", response_model=Rpc)
async def patch_rpc(
    rpc_id: str,
    rpc_data: RpcPatch,
    rpc_manager: Annotated[RpcManager, Depends(RpcManager)],
) -> Rpc:
    return Rpc.model_validate(await rpc_manager.patch(rpc_id, rpc_data))


@router.delete("/rpcs/{rpc_id}", response_model=None)
async def delete_rpc(rpc_id: str, rpc_manager: Annotated[RpcManager, Depends(RpcManager)]) -> None:
    await rpc_manager.delete(rpc_id)
