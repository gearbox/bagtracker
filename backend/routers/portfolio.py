from fastapi import APIRouter, Depends
from loguru import logger

from backend.managers import EthereumManager, PortfolioManager, WalletManager
from backend.schemas import Portfolio, PortfolioAll, PortfolioCreateOrUpdate, PortfolioPatch, Wallet

router = APIRouter()


@router.get("/portfolio-demo/{user_id}", response_model=dict)
def get_portfolio_demo(
        user_id: str, 
        wallet_manager: WalletManager = Depends(WalletManager),
        eth_manager: EthereumManager = Depends(EthereumManager),
    ) -> dict:
    wallets = wallet_manager.get_all_by_user(user_id)
    portfolio = []
    for wallet in wallets:
        wallet_model = Wallet.model_validate(wallet)
        chain = wallet_model.chain
        chain_name = chain.name if chain is not None else "Unknown"
        chain_native_symbol = chain.native_symbol if chain is not None else "Unknown"
        if chain_name == "eth":
            try:
                eth_balance = eth_manager.get_balance(wallet_model.address)
                erc20_balances = eth_manager.get_erc20_balances(wallet_model.address)
            except Exception as e:
                logger.error(f"Error fetching balances for wallet {wallet_model.address}: {e}")
                continue
            portfolio.append({
                "wallet": wallet_model.address,
                "blockchain": chain_name,
                "balances": [{"symbol": chain_native_symbol, "balance": eth_balance}] + erc20_balances
            })
    return {"user_id": user_id, "portfolio": portfolio}

@router.post("/portfolio/{username}", response_model=Portfolio)
def create_portfolio(
        username: str,
        portfolio: PortfolioCreateOrUpdate,
        portfolio_manager: PortfolioManager = Depends(PortfolioManager)
) -> Portfolio:
    return Portfolio.model_validate(portfolio_manager.create(portfolio, username))

@router.get("/portfolios/{username}", response_model=PortfolioAll)
def list_portfolios(
        username: str,
        portfolio_manager: PortfolioManager = Depends(PortfolioManager)
) -> PortfolioAll:
    return PortfolioAll.model_validate({"portfolios": portfolio_manager.get_all_by_user(username)})

@router.get("/portfolio/{portfolio_id}", response_model=Portfolio)
def get_portfolio(
        portfolio_id: str,
        portfolio_manager: PortfolioManager = Depends(PortfolioManager)
) -> Portfolio:
    return Portfolio.model_validate(portfolio_manager.get(portfolio_id))

@router.put("/portfolio/{portfolio_id}", response_model=Portfolio)
def update_portfolio(
        portfolio_id: str,
        portfolio_data: PortfolioCreateOrUpdate,
        portfolio_manager: PortfolioManager = Depends(PortfolioManager)
) -> Portfolio:
    return Portfolio.model_validate(portfolio_manager.update(portfolio_id, portfolio_data))

@router.patch("/portfolio/{portfolio_id}", response_model=Portfolio)
def patch_portfolio(
        portfolio_id: str,
        portfolio_data: PortfolioPatch,
        portfolio_manager: PortfolioManager = Depends(PortfolioManager)
) -> Portfolio:
    return Portfolio.model_validate(portfolio_manager.patch(portfolio_id, portfolio_data))

@router.delete("/portfolio/{portfolio_id}", response_model=None, status_code=204)
def delete_portfolio(
        portfolio_id: str,
        portfolio_manager: PortfolioManager = Depends(PortfolioManager)
) -> None:
    portfolio_manager.delete(portfolio_id)

@router.put("/portfolio/{portfolio_id}/add/{wallet_id}", status_code=204)
def add_wallet_to_portfolio(
        portfolio_id: str, 
        wallet_id: str,
        portfolio_manager: PortfolioManager = Depends(PortfolioManager),
    ):
    portfolio_manager.add_wallet_to_portfolio(portfolio_id, wallet_id)

@router.put("/portfolio/{portfolio_id}/remove/{wallet_id}", status_code=204)
def remove_wallet_from_portfolio(
        portfolio_id: str, 
        wallet_id: str,
        portfolio_manager: PortfolioManager = Depends(PortfolioManager),
    ):
    portfolio_manager.remove_wallet_from_portfolio(portfolio_id, wallet_id)