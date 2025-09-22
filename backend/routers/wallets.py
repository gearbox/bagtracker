from fastapi import APIRouter, Depends

from backend.managers import WalletManager
from backend.schemas import Wallet, WalletCreateOrUpdate, WalletPatch

router = APIRouter()


@router.post("/wallets/{username}", response_model=Wallet)
def add_wallet(
    username: str, 
    wallet: WalletCreateOrUpdate, 
    wallet_manager: WalletManager = Depends(WalletManager),
) -> Wallet:
    return Wallet.model_validate(wallet_manager.create(wallet, username))

@router.get("/wallets/{username}", response_model=list[Wallet])
def list_wallets(
    username: str, 
    wallet_manager: WalletManager = Depends(WalletManager),
 ) -> list[Wallet]:
    return [Wallet.model_validate(wallet) for wallet in wallet_manager.get_all_by_user(username)]

@router.get("/wallet/{wallet_id}", response_model=Wallet)
def get_wallet(
        wallet_id: str, 
        wallet_manager: WalletManager = Depends(WalletManager)
    ) -> Wallet:
    return Wallet.model_validate(wallet_manager.get(wallet_id))

@router.put("/wallet/{wallet_id}", response_model=Wallet)
def update_wallet(
    wallet_id: str, 
    wallet_data: WalletCreateOrUpdate, 
    wallet_manager: WalletManager = Depends(WalletManager)
) -> Wallet:
    return Wallet.model_validate(wallet_manager.update(wallet_id, wallet_data))

@router.patch("/wallet/{wallet_id}", response_model=Wallet)
def patch_wallet(
    wallet_id: str, 
    wallet_data: WalletPatch,
    wallet_manager: WalletManager = Depends(WalletManager)
) -> Wallet:
    return Wallet.model_validate(wallet_manager.patch(wallet_id, wallet_data))

@router.delete("/wallet/{wallet_id}", response_model=None, status_code=204)
def delete_wallet(
    wallet_id: str, 
    wallet_manager: WalletManager = Depends(WalletManager)
) -> None:
    wallet_manager.delete(wallet_id)
