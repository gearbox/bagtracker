from typing import List

from fastapi import APIRouter, Depends

from backend.schemas import Wallet
from backend.managers import WalletManager, EthereumManager

router = APIRouter()


@router.get("/portfolio/{user_id}", response_model=dict)
def get_portfolio(
        user_id: str, 
        wallet_manager: WalletManager = Depends(WalletManager),
        eth_manager: EthereumManager = Depends(EthereumManager),
    ) -> dict:
    wallets = wallet_manager.get_wallets_by_user(user_id)
    portfolio = []
    for wallet in wallets:
        if wallet.blockchain == "ethereum":
            eth_balance = eth_manager.get_balance(wallet.address)
            erc20_balances = eth_manager.get_erc20_balances(wallet.address)
            portfolio.append({
                "wallet": wallet.address,
                "blockchain": wallet.blockchain,
                "balances": [{"symbol": "ETH", "balance": eth_balance}] + erc20_balances
            })
    return {"user_id": user_id, "portfolio": portfolio}
