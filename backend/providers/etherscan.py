"""
Etherscan API Provider
Supports multiple EVM chains via Etherscan-like explorers.
"""

from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

import httpx
from loguru import logger

from backend.settings import Settings, settings


class EtherscanChain(str, Enum):
    """Supported Etherscan-like explorer chains."""

    ETHEREUM = "ethereum"
    BSC = "bsc"
    POLYGON = "polygon"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"
    BASE = "base"


class EtherscanProvider:
    """
    Provider for fetching transaction data from Etherscan-like APIs.

    Supports multiple EVM chains with their respective explorer APIs.
    """

    # Base URLs for different chains
    BASE_URLS = {
        EtherscanChain.ETHEREUM: "https://api.etherscan.io/api",
        EtherscanChain.BSC: "https://api.bscscan.com/api",
        EtherscanChain.POLYGON: "https://api.polygonscan.com/api",
        EtherscanChain.ARBITRUM: "https://api.arbiscan.io/api",
        EtherscanChain.OPTIMISM: "https://api-optimistic.etherscan.io/api",
        EtherscanChain.BASE: "https://api.basescan.org/api",
    }

    def __init__(self, chain: EtherscanChain | str, settings_obj: Settings | None = None):
        """
        Initialize Etherscan provider.

        Args:
            chain: Chain to use (ethereum, bsc, polygon, etc.)
            settings_obj: Settings instance (defaults to global settings)
        """
        self.chain = EtherscanChain(chain) if isinstance(chain, str) else chain
        self.settings = settings_obj or settings
        self.base_url = self.BASE_URLS[self.chain]
        self.api_key = self._get_api_key()

    def _get_api_key(self) -> str | None:
        """Get API key for the current chain."""
        key_mapping = {
            EtherscanChain.ETHEREUM: self.settings.etherscan_api_key,
            EtherscanChain.BSC: self.settings.bscscan_api_key,
            EtherscanChain.POLYGON: self.settings.polygonscan_api_key,
            EtherscanChain.ARBITRUM: self.settings.arbiscan_api_key,
            EtherscanChain.OPTIMISM: self.settings.optimism_etherscan_api_key,
            EtherscanChain.BASE: self.settings.basescan_api_key,
        }
        return key_mapping.get(self.chain)

    async def get_normal_transactions(
        self,
        address: str,
        start_block: int = 0,
        end_block: int = 99999999,
        page: int = 1,
        offset: int = 100,
        sort: str = "asc",
    ) -> list[dict[str, Any]]:
        """
        Fetch normal (native token) transactions for an address.

        Args:
            address: Wallet address
            start_block: Starting block number (default: 0)
            end_block: Ending block number (default: 99999999 = latest)
            page: Page number (default: 1)
            offset: Number of transactions per page (max: 10000, default: 100)
            sort: Sort order - 'asc' or 'desc' (default: 'asc')

        Returns:
            List of transaction dictionaries
        """
        params = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": page,
            "offset": offset,
            "sort": sort,
        }

        if self.api_key:
            params["apikey"] = self.api_key

        return await self._make_request(params)

    async def get_erc20_transfers(
        self,
        address: str,
        contract_address: str | None = None,
        start_block: int = 0,
        end_block: int = 99999999,
        page: int = 1,
        offset: int = 100,
        sort: str = "asc",
    ) -> list[dict[str, Any]]:
        """
        Fetch ERC20 token transfer events for an address.

        Args:
            address: Wallet address
            contract_address: Filter by specific token contract (optional)
            start_block: Starting block number (default: 0)
            end_block: Ending block number (default: 99999999 = latest)
            page: Page number (default: 1)
            offset: Number of transfers per page (max: 10000, default: 100)
            sort: Sort order - 'asc' or 'desc' (default: 'asc')

        Returns:
            List of transfer event dictionaries
        """
        params = {
            "module": "account",
            "action": "tokentx",
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": page,
            "offset": offset,
            "sort": sort,
        }

        if contract_address:
            params["contractaddress"] = contract_address

        if self.api_key:
            params["apikey"] = self.api_key

        return await self._make_request(params)

    async def get_erc721_transfers(
        self,
        address: str,
        contract_address: str | None = None,
        start_block: int = 0,
        end_block: int = 99999999,
        page: int = 1,
        offset: int = 100,
        sort: str = "asc",
    ) -> list[dict[str, Any]]:
        """
        Fetch ERC721 (NFT) transfer events for an address.

        Args:
            address: Wallet address
            contract_address: Filter by specific NFT contract (optional)
            start_block: Starting block number (default: 0)
            end_block: Ending block number (default: 99999999 = latest)
            page: Page number (default: 1)
            offset: Number of transfers per page (max: 10000, default: 100)
            sort: Sort order - 'asc' or 'desc' (default: 'asc')

        Returns:
            List of NFT transfer event dictionaries
        """
        params = {
            "module": "account",
            "action": "tokennfttx",
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": page,
            "offset": offset,
            "sort": sort,
        }

        if contract_address:
            params["contractaddress"] = contract_address

        if self.api_key:
            params["apikey"] = self.api_key

        return await self._make_request(params)

    async def get_erc1155_transfers(
        self,
        address: str,
        contract_address: str | None = None,
        start_block: int = 0,
        end_block: int = 99999999,
        page: int = 1,
        offset: int = 100,
        sort: str = "asc",
    ) -> list[dict[str, Any]]:
        """
        Fetch ERC1155 (multi-token) transfer events for an address.

        Args:
            address: Wallet address
            contract_address: Filter by specific contract (optional)
            start_block: Starting block number (default: 0)
            end_block: Ending block number (default: 99999999 = latest)
            page: Page number (default: 1)
            offset: Number of transfers per page (max: 10000, default: 100)
            sort: Sort order - 'asc' or 'desc' (default: 'asc')

        Returns:
            List of ERC1155 transfer event dictionaries
        """
        params = {
            "module": "account",
            "action": "token1155tx",
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": page,
            "offset": offset,
            "sort": sort,
        }

        if contract_address:
            params["contractaddress"] = contract_address

        if self.api_key:
            params["apikey"] = self.api_key

        return await self._make_request(params)

    async def get_internal_transactions(
        self,
        address: str,
        start_block: int = 0,
        end_block: int = 99999999,
        page: int = 1,
        offset: int = 100,
        sort: str = "asc",
    ) -> list[dict[str, Any]]:
        """
        Fetch internal transactions (contract interactions) for an address.

        Args:
            address: Wallet address
            start_block: Starting block number (default: 0)
            end_block: Ending block number (default: 99999999 = latest)
            page: Page number (default: 1)
            offset: Number of transactions per page (max: 10000, default: 100)
            sort: Sort order - 'asc' or 'desc' (default: 'asc')

        Returns:
            List of internal transaction dictionaries
        """
        params = {
            "module": "account",
            "action": "txlistinternal",
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": page,
            "offset": offset,
            "sort": sort,
        }

        if self.api_key:
            params["apikey"] = self.api_key

        return await self._make_request(params)

    async def _make_request(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Make an API request to Etherscan.

        Args:
            params: Query parameters

        Returns:
            List of results from the API

        Raises:
            httpx.HTTPError: If the request fails
            ValueError: If the API returns an error
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                logger.debug(f"Etherscan API request: {self.base_url} with params: {params}")
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()

                data = response.json()

                # Check API response status
                if data.get("status") == "0":
                    # Status 0 can mean error or no results
                    message = data.get("message", "Unknown error")
                    if message == "No transactions found":
                        logger.info(f"No transactions found for address {params.get('address')}")
                        return []
                    else:
                        logger.error(f"Etherscan API error: {message}")
                        raise ValueError(f"Etherscan API error: {message}")

                result = data.get("result", [])

                # Ensure result is a list
                if not isinstance(result, list):
                    logger.warning(f"Unexpected result type from Etherscan: {type(result)}")
                    return []

                logger.info(f"Fetched {len(result)} transactions from Etherscan")
                return result

            except httpx.HTTPError as e:
                logger.error(f"HTTP error while fetching from Etherscan: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error while fetching from Etherscan: {e}")
                raise

    @staticmethod
    def parse_transaction(tx: dict[str, Any]) -> dict[str, Any]:
        """
        Parse a transaction from Etherscan format to a normalized format.

        Args:
            tx: Raw transaction data from Etherscan

        Returns:
            Normalized transaction dictionary
        """
        return {
            "hash": tx.get("hash"),
            "block_number": int(tx.get("blockNumber", 0)),
            "timestamp": datetime.fromtimestamp(int(tx.get("timeStamp", 0)), tz=UTC),
            "from_address": tx.get("from", "").lower(),
            "to_address": tx.get("to", "").lower(),
            "value": Decimal(tx.get("value", 0)),
            "gas_used": int(tx.get("gasUsed", 0)),
            "gas_price": Decimal(tx.get("gasPrice", 0)),
            "is_error": tx.get("isError", "0") == "1",
            "transaction_index": int(tx.get("transactionIndex", 0)),
            "confirmations": int(tx.get("confirmations", 0)),
            "contract_address": tx.get("contractAddress", "").lower() if tx.get("contractAddress") else None,
            "input": tx.get("input", ""),
        }

    @staticmethod
    def parse_erc20_transfer(transfer: dict[str, Any]) -> dict[str, Any]:
        """
        Parse an ERC20 transfer event from Etherscan format to a normalized format.

        Args:
            transfer: Raw ERC20 transfer data from Etherscan

        Returns:
            Normalized transfer dictionary
        """
        return {
            "hash": transfer.get("hash"),
            "block_number": int(transfer.get("blockNumber", 0)),
            "timestamp": datetime.fromtimestamp(int(transfer.get("timeStamp", 0)), tz=UTC),
            "from_address": transfer.get("from", "").lower(),
            "to_address": transfer.get("to", "").lower(),
            "value": Decimal(transfer.get("value", 0)),
            "token_name": transfer.get("tokenName", ""),
            "token_symbol": transfer.get("tokenSymbol", ""),
            "token_decimals": int(transfer.get("tokenDecimal", 0)),
            "contract_address": transfer.get("contractAddress", "").lower(),
            "gas_used": int(transfer.get("gasUsed", 0)),
            "gas_price": Decimal(transfer.get("gasPrice", 0)),
            "transaction_index": int(transfer.get("transactionIndex", 0)),
            "confirmations": int(transfer.get("confirmations", 0)),
        }
