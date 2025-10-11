from typing import Annotated

from fastapi import APIRouter, Depends

from backend.managers import TokenManager
from backend.schemas import Token, TokenAll, TokenCreateOrUpdate, TokenPatch

router = APIRouter()


@router.post("/tokens/", response_model=Token)
async def create_token(
    token: TokenCreateOrUpdate,
    token_manager: Annotated[TokenManager, Depends(TokenManager)],
) -> Token:
    await token_manager.sync_sequence()
    return Token.model_validate(await token_manager.create_from_schema(token))


@router.get("/tokens/", response_model=TokenAll)
async def list_tokens(
    token_manager: Annotated[TokenManager, Depends(TokenManager)],
) -> TokenAll:
    return TokenAll.model_validate({"tokens": await token_manager.get_all()})


@router.get("/tokens/{token_id}", response_model=Token)
async def get_token(token_id: int | str, token_manager: Annotated[TokenManager, Depends(TokenManager)]) -> Token:
    return Token.model_validate(await token_manager.get(token_id))


@router.put("/tokens/{token_id}", response_model=Token)
async def update_token(
    token_id: str,
    token_data: TokenCreateOrUpdate,
    token_manager: Annotated[TokenManager, Depends(TokenManager)],
) -> Token:
    return Token.model_validate(await token_manager.update(token_id, token_data))


@router.patch("/tokens/{token_id}", response_model=Token)
async def patch_token(
    token_id: str,
    token_data: TokenPatch,
    token_manager: Annotated[TokenManager, Depends(TokenManager)],
) -> Token:
    return Token.model_validate(await token_manager.patch(token_id, token_data))


@router.delete("/tokens/{token_id}", response_model=None)
async def delete_token(token_id: str, token_manager: Annotated[TokenManager, Depends(TokenManager)]) -> None:
    await token_manager.delete(token_id)
