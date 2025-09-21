from fastapi import APIRouter, Depends

from backend.managers import EthereumManager, WalletManager
from backend.schemas import Wallet

router = APIRouter()


@router.get("/portfolio/{user_id}", response_model=dict)
def get_portfolio(
        user_id: str, 
        wallet_manager: WalletManager = Depends(WalletManager),
        eth_manager: EthereumManager = Depends(EthereumManager),
    ) -> dict:
    wallets = wallet_manager.get_all_by_user(user_id)
    portfolio = []
    for wallet in wallets:
        print(f"Wallet db object: {wallet}")
        wallet_model = Wallet.model_validate(wallet)
        print(f"Validated Wallet: {wallet_model}")
        chain = wallet_model.chain
        chain_name = chain.name if chain is not None else "Unknown"
        chain_native_symbol = chain.native_symbol if chain is not None else "Unknown"
        print(f"Chain Name: {chain_name}")
        if chain_name == "eth":
            try:
                eth_balance = eth_manager.get_balance(wallet_model.address)
                erc20_balances = eth_manager.get_erc20_balances(wallet_model.address)
            except Exception as e:
                print(f"Error fetching balances for wallet {wallet_model.address}: {e}")
                continue
            portfolio.append({
                "wallet": wallet_model.address,
                "blockchain": chain_name,
                "balances": [{"symbol": chain_native_symbol, "balance": eth_balance}] + erc20_balances
            })
    return {"user_id": user_id, "portfolio": portfolio}
