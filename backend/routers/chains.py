from typing import Annotated

from fastapi import APIRouter, Depends

from backend.managers import ChainManager
from backend.schemas import Chain, ChainCreateOrUpdate, ChainPatch

router = APIRouter()


@router.post("/chains/", response_model=Chain)
async def create_chain(
    chain: ChainCreateOrUpdate,
    chain_manager: Annotated[ChainManager, Depends(ChainManager)],
) -> Chain:
    await chain_manager.sync_sequence()
    return Chain.model_validate(await chain_manager.create_from_schema(chain))


@router.get("/chains/", response_model=list[Chain])
async def list_chains(
    chain_manager: Annotated[ChainManager, Depends(ChainManager)],
) -> list[Chain]:
    chains = await chain_manager.get_all()
    return [Chain.model_validate(chain) for chain in chains]


@router.get("/chains/{chain_id}", response_model=Chain)
async def get_chain(chain_id: int | str, chain_manager: Annotated[ChainManager, Depends(ChainManager)]) -> Chain:
    return Chain.model_validate(await chain_manager.get(chain_id))


@router.put("/chains/{chain_id}", response_model=Chain)
async def update_chain(
    chain_id: str,
    chain_data: ChainCreateOrUpdate,
    chain_manager: Annotated[ChainManager, Depends(ChainManager)],
) -> Chain:
    return Chain.model_validate(await chain_manager.update(chain_id, chain_data))


@router.patch("/chains/{chain_id}", response_model=Chain)
async def patch_chain(
    chain_id: str,
    chain_data: ChainPatch,
    chain_manager: Annotated[ChainManager, Depends(ChainManager)],
) -> Chain:
    return Chain.model_validate(await chain_manager.patch(chain_id, chain_data))


@router.delete("/chains/{chain_id}", response_model=None)
async def delete_chain(chain_id: str, chain_manager: Annotated[ChainManager, Depends(ChainManager)]) -> None:
    await chain_manager.delete(chain_id)
