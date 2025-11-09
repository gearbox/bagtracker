from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as status_code

from backend.managers import WalletManager
from backend.schemas import (
    Wallet,
    WalletAddChain,
    WalletAddressResponse,
    WalletAll,
    WalletCreateMultichain,
    WalletCreateOrUpdate,
    WalletPatch,
    WalletResponse,
)

router = APIRouter()


@router.post("/wallet/{username}", response_model=WalletResponse)
async def create_multichain_wallet(
    username: str,
    wallet_data: WalletCreateMultichain,
    wallet_manager: Annotated[WalletManager, Depends(WalletManager)],
) -> WalletResponse:
    """
    Create a new multichain wallet with addresses on multiple chains.
    """
    wallet = await wallet_manager.create_multichain_wallet(wallet_data, username)
    return WalletResponse.model_validate(wallet)


@router.post(
    "/wallet/{wallet_id}/chain", response_model=WalletAddressResponse, status_code=status_code.HTTP_201_CREATED
)
async def add_chain_to_wallet(
    wallet_id: str,
    chain_data: WalletAddChain,
    wallet_manager: Annotated[WalletManager, Depends(WalletManager)],
) -> WalletAddressResponse:
    """
    Add a new chain to an existing wallet.
    """
    try:
        wallet_address = await wallet_manager.add_chain(UUID(wallet_id), chain_data)
        return WalletAddressResponse.model_validate(wallet_address)
    except ValueError as e:
        raise HTTPException(status_code=status_code.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.delete("/wallet/{wallet_id}/chain/{chain_id}", status_code=status_code.HTTP_204_NO_CONTENT)
async def remove_chain_from_wallet(
    wallet_id: str,
    chain_id: int,
    wallet_manager: Annotated[WalletManager, Depends(WalletManager)],
) -> None:
    """
    Remove a chain from a wallet.

    Note: This deactivates the chain rather than deleting it
    to preserve transaction history.
    """
    await wallet_manager.remove_chain(UUID(wallet_id), chain_id)


@router.get("/user/wallets/{username}", response_model=WalletAll, tags=["Users"])
async def list_wallets(
    username: str,
    wallet_manager: Annotated[WalletManager, Depends(WalletManager)],
) -> WalletAll:
    return WalletAll.model_validate({"wallets": await wallet_manager.get_all_by_user(username)})


@router.get("/wallet/{wallet_id}", response_model=Wallet)
async def get_wallet(wallet_id: str, wallet_manager: Annotated[WalletManager, Depends(WalletManager)]) -> Wallet:
    return Wallet.model_validate(await wallet_manager.get(wallet_id))


@router.get("/wallet/address/{address}/chain/{chain_id}", response_model=WalletResponse)
async def get_wallet_by_address_and_chain(
    address: str, chain_id: int, wallet_manager: Annotated[WalletManager, Depends(WalletManager)]
) -> WalletResponse:
    """Find wallet by address on a specific chain."""
    wallet = await wallet_manager.get_by_address_and_chain(address, chain_id)

    if not wallet:
        raise HTTPException(
            status_code=status_code.HTTP_404_NOT_FOUND,
            detail=f"No wallet found with address {address} on chain {chain_id}",
        )

    return WalletResponse.model_validate(wallet)


@router.get("/wallet/address/{address}", response_model=WalletResponse)
async def get_wallet_by_address(
    address: str, wallet_manager: Annotated[WalletManager, Depends(WalletManager)]
) -> WalletResponse | None:
    return WalletResponse.model_validate(await wallet_manager.get_by_address(address))


@router.put("/wallet/{wallet_id}", response_model=Wallet)
async def update_wallet(
    wallet_id: str, wallet_data: WalletCreateOrUpdate, wallet_manager: Annotated[WalletManager, Depends(WalletManager)]
) -> Wallet:
    return Wallet.model_validate(await wallet_manager.update(wallet_id, wallet_data))


@router.patch("/wallet/{wallet_id}", response_model=Wallet)
async def patch_wallet(
    wallet_id: str, wallet_data: WalletPatch, wallet_manager: Annotated[WalletManager, Depends(WalletManager)]
) -> Wallet:
    return Wallet.model_validate(await wallet_manager.patch(wallet_id, wallet_data))


@router.delete("/wallet/{wallet_id}", response_model=None, status_code=204)
async def delete_wallet(wallet_id: str, wallet_manager: Annotated[WalletManager, Depends(WalletManager)]) -> None:
    await wallet_manager.delete(wallet_id)
