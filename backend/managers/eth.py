from typing import Union
import decimal

from fastapi import Depends
from web3 import Web3
from eth_typing import (
    Address,
    ChecksumAddress,
)

from backend.providers.eth import get_provider


class EthereumManager:
    def __init__(
        self, 
        provider: Web3 = Depends(get_provider)
    ) -> None:
        self.provider = provider

    def get_balance(self, address: str | Address | ChecksumAddress) -> Union[int, decimal.Decimal]:
        if isinstance(address, str):
            address = Web3.to_checksum_address(address)
        balance_wei = self.provider.eth.get_balance(address)
        return self.provider.from_wei(balance_wei, 'ether')
