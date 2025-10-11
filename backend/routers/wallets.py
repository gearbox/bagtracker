from typing import Annotated

from fastapi import APIRouter, Depends

from backend.managers import WalletManager
from backend.schemas import Wallet, WalletAll, WalletCreateOrUpdate, WalletPatch

router = APIRouter()


@router.post("/wallet/{username}", response_model=Wallet)
async def add_wallet(
    username: str,
    wallet: WalletCreateOrUpdate,
    wallet_manager: Annotated[WalletManager, Depends(WalletManager)],
) -> Wallet:
    return Wallet.model_validate(await wallet_manager.create_from_schema(wallet, username))


@router.get("/user/wallets/{username}", response_model=WalletAll, tags=["Users"])
async def list_wallets(
    username: str,
    wallet_manager: Annotated[WalletManager, Depends(WalletManager)],
) -> WalletAll:
    return WalletAll.model_validate({"wallets": await wallet_manager.get_all_by_user(username)})


@router.get("/wallet/{wallet_id}", response_model=Wallet)
async def get_wallet(wallet_id: str, wallet_manager: Annotated[WalletManager, Depends(WalletManager)]) -> Wallet:
    return Wallet.model_validate(await wallet_manager.get(wallet_id))


@router.get("/wallet/address/{address}", response_model=Wallet)
async def get_wallet_by_address(
    address: str, wallet_manager: Annotated[WalletManager, Depends(WalletManager)]
) -> Wallet | None:
    return Wallet.model_validate(await wallet_manager.get_by_address(address))


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
