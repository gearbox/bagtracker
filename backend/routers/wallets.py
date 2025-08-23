from typing import List

from fastapi import APIRouter, Depends

from backend.schemas import Wallet, WalletCreate
from backend.managers import WalletManager

router = APIRouter()


@router.post("/wallets/{username}", response_model=Wallet)
def add_wallet(
    username: str, 
    wallet: WalletCreate, 
    wallet_manager: WalletManager = Depends(WalletManager),
) -> Wallet:
    return Wallet.model_validate(wallet_manager.create_wallet(wallet, username).to_schema())

@router.get("/wallets/{username}", response_model=list[Wallet])
def list_wallets(
    username: str, 
    wallet_manager: WalletManager = Depends(WalletManager),
 ) -> List[Wallet]:
    return [Wallet.model_validate(wallet.to_schema()) for wallet in wallet_manager.get_wallets_by_user(username)]

@router.get("/wallet/{wallet_id}", response_model=Wallet)
def get_wallet(
        wallet_id: str, 
        wallet_manager: WalletManager = Depends(WalletManager)
    ) -> Wallet:
    return Wallet.model_validate(wallet_manager.get_wallet(wallet_id).to_schema())

@router.put("/wallet/{wallet_id}", response_model=Wallet)
def update_wallet(
    wallet_id: str, 
    wallet_data: WalletCreate, 
    wallet_manager: WalletManager = Depends(WalletManager)
) -> Wallet:
    return Wallet.model_validate(wallet_manager.update_wallet(wallet_id, wallet_data).to_schema())

@router.delete("/wallet/{wallet_id}", response_model=None)
def delete_wallet(
    wallet_id: str, 
    wallet_manager: WalletManager = Depends(WalletManager)
) -> None:
    wallet_manager.delete_wallet(wallet_id)
