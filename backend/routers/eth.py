from fastapi import APIRouter, Depends, Response
from fastapi import status as status_code
from eth_typing import (
    Address,
    ChecksumAddress,
)

from backend.managers import EthereumManager

router = APIRouter()


@router.get("/balance/{address}")
def get_balance(
    address: str,
    manager: EthereumManager = Depends(EthereumManager)
):
    balance = manager.get_balance(address)
    return {"address": address, "eth_balance": balance}
