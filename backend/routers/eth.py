from typing import Annotated

from fastapi import APIRouter, Depends

from backend.managers import EthereumManager

router = APIRouter()


@router.get("/eth-balance/{address}")
def get_eth_balance(
    address: str,
    manager: Annotated[EthereumManager, Depends(EthereumManager)],
):
    balance = manager.get_balance(address)
    return {"address": address, "eth_balance": balance}


@router.get("/balance/{address}")
def get_balance(
    address: str,
    manager: Annotated[EthereumManager, Depends(EthereumManager)],
):
    eth_balance = manager.get_balance(address)
    erc20_balances = manager.get_erc20_balances(address)
    portfolio = {
        "address": address,
        "blockchain": "Ethereum",
        "balances": [{"symbol": "ETH", "balance": eth_balance}] + erc20_balances,
    }
    return portfolio
