from typing import Annotated

from fastapi import APIRouter, Depends
from loguru import logger

from backend.managers import EthereumManager, PortfolioManager, WalletManager
from backend.schemas import Portfolio, PortfolioAll, PortfolioCreateOrUpdate, PortfolioPatch

router = APIRouter()


@router.get("/portfolio-demo/{user_id}", response_model=dict)
async def get_portfolio_demo(
    user_id: str,
    wallet_manager: Annotated[WalletManager, Depends(WalletManager)],
    eth_manager: Annotated[EthereumManager, Depends(EthereumManager)],
) -> dict:
    wallets = await wallet_manager.get_all_by_user(user_id)
    portfolio = []
    for wallet in wallets:
        chain = wallet.chain
        chain_name = chain.name if chain is not None else "Unknown"

        # Get native token symbol from tokens table
        native_token = next((token for token in chain.tokens if token.is_native), None) if chain else None
        chain_native_symbol = native_token.symbol if native_token else "Unknown"

        if chain_name == "eth-mainnet":
            try:
                eth_balance = eth_manager.get_balance(wallet.address)
                erc20_balances = eth_manager.get_erc20_balances(wallet.address)
            except Exception as e:
                logger.error(f"Error fetching balances for wallet {wallet.address}: {e}")
                continue
            portfolio.append(
                {
                    "wallet": wallet.address,
                    "blockchain": chain_name,
                    "balances": [{"symbol": chain_native_symbol, "balance": eth_balance}] + erc20_balances,
                }
            )
    return {"user_id": user_id, "portfolio": portfolio}


@router.post("/portfolio/{username}", response_model=Portfolio)
async def create_portfolio(
    username: str,
    portfolio: PortfolioCreateOrUpdate,
    portfolio_manager: Annotated[PortfolioManager, Depends(PortfolioManager)],
) -> Portfolio:
    return Portfolio.model_validate(await portfolio_manager.create(portfolio, username))


@router.get("/portfolios/{username}", response_model=PortfolioAll)
async def list_portfolios(
    username: str, portfolio_manager: Annotated[PortfolioManager, Depends(PortfolioManager)]
) -> PortfolioAll:
    return PortfolioAll.model_validate({"portfolios": await portfolio_manager.get_all_by_user(username)})


@router.get("/portfolio/{portfolio_id}", response_model=Portfolio)
async def get_portfolio(
    portfolio_id: str, portfolio_manager: Annotated[PortfolioManager, Depends(PortfolioManager)]
) -> Portfolio:
    return Portfolio.model_validate(await portfolio_manager.get(portfolio_id))


@router.put("/portfolio/{portfolio_id}", response_model=Portfolio)
async def update_portfolio(
    portfolio_id: str,
    portfolio_data: PortfolioCreateOrUpdate,
    portfolio_manager: Annotated[PortfolioManager, Depends(PortfolioManager)],
) -> Portfolio:
    return Portfolio.model_validate(await portfolio_manager.update(portfolio_id, portfolio_data))


@router.patch("/portfolio/{portfolio_id}", response_model=Portfolio)
async def patch_portfolio(
    portfolio_id: str,
    portfolio_data: PortfolioPatch,
    portfolio_manager: Annotated[PortfolioManager, Depends(PortfolioManager)],
) -> Portfolio:
    return Portfolio.model_validate(await portfolio_manager.patch(portfolio_id, portfolio_data))


@router.delete("/portfolio/{portfolio_id}", response_model=None, status_code=204)
async def delete_portfolio(
    portfolio_id: str, portfolio_manager: Annotated[PortfolioManager, Depends(PortfolioManager)]
) -> None:
    await portfolio_manager.delete(portfolio_id)


@router.put("/portfolio/{portfolio_id}/add/{wallet_id}", status_code=204)
async def add_wallet_to_portfolio(
    portfolio_id: str,
    wallet_id: str,
    portfolio_manager: Annotated[PortfolioManager, Depends(PortfolioManager)],
):
    await portfolio_manager.add_wallet_to_portfolio(portfolio_id, wallet_id)


@router.put("/portfolio/{portfolio_id}/remove/{wallet_id}", status_code=204)
async def remove_wallet_from_portfolio(
    portfolio_id: str,
    wallet_id: str,
    portfolio_manager: Annotated[PortfolioManager, Depends(PortfolioManager)],
):
    await portfolio_manager.remove_wallet_from_portfolio(portfolio_id, wallet_id)
