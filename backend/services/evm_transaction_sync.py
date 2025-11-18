"""
EVM Transaction Sync Service
Syncs transactions from Etherscan-like APIs for EVM wallet addresses.
"""

from datetime import UTC, datetime
from decimal import Decimal

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.databases.models import Chain, Token, Transaction, WalletAddress
from backend.errors import WalletError
from backend.managers import BalanceManager, TokenManager
from backend.providers.etherscan import EtherscanChain, EtherscanProvider
from backend.schemas import TransactionStatus, TransactionType
from backend.settings import Settings


class EVMTransactionSyncService:
    """
    Service for syncing EVM transactions from Etherscan-like APIs.

    Features:
    - Syncs both native token transactions and ERC20 transfers
    - Idempotent: Re-running sync yields the same result (skips existing transactions)
    - Automatically creates Token records for unknown ERC20 tokens
    - Updates wallet last_sync_block after successful sync
    - Processes balances using FIFO calculator
    """

    def __init__(self, session: AsyncSession, settings: Settings):
        """
        Initialize sync service.

        Args:
            session: Database session
            settings: Application settings
        """
        self.session = session
        self.settings = settings

    async def sync_wallet_address_transactions(
        self,
        wallet_address_id: int,
        start_block: int | None = None,
        end_block: int = 99999999,
        process_balances: bool = True,
    ) -> dict:
        """
        Sync all transactions for a wallet address.

        Args:
            wallet_address_id: WalletAddress ID to sync
            start_block: Starting block (defaults to last_sync_block or 0)
            end_block: Ending block (default: 99999999 = latest)
            process_balances: Whether to update balances (default: True)

        Returns:
            Dictionary with sync results:
            {
                "address": str,
                "chain": str,
                "native_transactions": int,
                "erc20_transfers": int,
                "total_synced": int,
                "start_block": int,
                "end_block": int,
            }
        """
        # Get wallet address with relationships
        wallet_address = await self.session.get(
            WalletAddress, wallet_address_id, options=[WalletAddress.chain, WalletAddress.wallet]
        )

        if not wallet_address:
            raise WalletError(404, f"WalletAddress {wallet_address_id} not found")

        # Determine start block
        if start_block is None:
            start_block = wallet_address.last_sync_block or 0

        logger.info(
            f"Starting sync for address {wallet_address.address} on chain {wallet_address.chain.name} "
            f"from block {start_block} to {end_block}"
        )

        # Map chain to Etherscan chain
        etherscan_chain = self._map_chain_to_etherscan(wallet_address.chain)

        # Initialize provider
        provider = EtherscanProvider(chain=etherscan_chain, settings_obj=self.settings)

        # Sync native transactions
        native_count = await self._sync_native_transactions(
            provider=provider,
            wallet_address=wallet_address,
            start_block=start_block,
            end_block=end_block,
            process_balances=process_balances,
        )

        # Sync ERC20 transfers
        erc20_count = await self._sync_erc20_transfers(
            provider=provider,
            wallet_address=wallet_address,
            start_block=start_block,
            end_block=end_block,
            process_balances=process_balances,
        )

        # Update last sync info
        await wallet_address.update(
            self.session,
            {
                "last_sync_block": end_block if end_block != 99999999 else None,
                "last_sync_at": datetime.now(UTC),
            },
        )

        await self.session.commit()

        logger.info(
            f"Sync completed: {native_count} native transactions, {erc20_count} ERC20 transfers "
            f"for address {wallet_address.address}"
        )

        return {
            "address": wallet_address.address,
            "chain": wallet_address.chain.name,
            "native_transactions": native_count,
            "erc20_transfers": erc20_count,
            "total_synced": native_count + erc20_count,
            "start_block": start_block,
            "end_block": end_block,
        }

    async def _sync_native_transactions(
        self,
        provider: EtherscanProvider,
        wallet_address: WalletAddress,
        start_block: int,
        end_block: int,
        process_balances: bool,
    ) -> int:
        """Sync native token (ETH, BNB, etc.) transactions."""
        transactions = await provider.get_normal_transactions(
            address=wallet_address.address, start_block=start_block, end_block=end_block, offset=1000, sort="asc"
        )

        logger.info(f"Fetched {len(transactions)} native transactions from Etherscan")

        synced_count = 0

        for tx_data in transactions:
            try:
                # Check if transaction already exists
                if await self._transaction_exists(tx_data["hash"], wallet_address.chain_id):
                    logger.debug(f"Transaction {tx_data['hash']} already exists, skipping")
                    continue

                # Get native token for this chain
                native_token = await self._get_native_token(wallet_address.chain_id)

                # Parse transaction
                parsed_tx = provider.parse_transaction(tx_data)

                # Determine transaction type
                tx_type = self._determine_transaction_type(parsed_tx, wallet_address.address_lowercase)

                # Calculate amount based on transaction type
                amount = parsed_tx["value"]

                # Create transaction record
                # Determine status based on error flag
                tx_status = (
                    TransactionStatus.FAILED.value if parsed_tx["is_error"] else TransactionStatus.CONFIRMED.value
                )

                transaction = Transaction(
                    wallet_id=wallet_address.wallet_id,
                    chain_id=wallet_address.chain_id,
                    token_id=native_token.id,
                    transaction_hash=parsed_tx["hash"],
                    block_number=parsed_tx["block_number"],
                    transaction_index=parsed_tx["transaction_index"],
                    transaction_type=tx_type.value,
                    status=tx_status,
                    counterparty_address=parsed_tx["to_address"]
                    if tx_type in (TransactionType.TRANSFER_OUT, TransactionType.SELL)
                    else parsed_tx["from_address"],
                    amount=amount,
                    gas_used=parsed_tx["gas_used"],
                    gas_price=parsed_tx["gas_price"],
                    fee_value=Decimal(parsed_tx["gas_used"]) * parsed_tx["gas_price"] / Decimal(10**18),
                    fee_currency="USD",
                    block_timestamp=parsed_tx["timestamp"],
                    timestamp=parsed_tx["timestamp"],
                )

                await transaction.save(self.session)

                # Process balance if requested and transaction is confirmed
                if process_balances and transaction.status == TransactionStatus.CONFIRMED.value:
                    balance_manager = BalanceManager(self.session, self.settings)
                    await balance_manager.process_transaction(transaction=transaction, create_snapshot=True)

                synced_count += 1
                logger.debug(f"Created transaction {transaction.transaction_hash}")

            except Exception as e:
                logger.error(f"Error processing native transaction {tx_data.get('hash')}: {e}")
                # Continue with next transaction instead of failing entire sync
                continue

        return synced_count

    async def _sync_erc20_transfers(
        self,
        provider: EtherscanProvider,
        wallet_address: WalletAddress,
        start_block: int,
        end_block: int,
        process_balances: bool,
    ) -> int:
        """Sync ERC20 token transfers."""
        transfers = await provider.get_erc20_transfers(
            address=wallet_address.address, start_block=start_block, end_block=end_block, offset=1000, sort="asc"
        )

        logger.info(f"Fetched {len(transfers)} ERC20 transfers from Etherscan")

        synced_count = 0

        for transfer_data in transfers:
            try:
                # Check if transaction already exists
                if await self._transaction_exists(transfer_data["hash"], wallet_address.chain_id):
                    logger.debug(f"Transfer {transfer_data['hash']} already exists, skipping")
                    continue

                # Parse transfer
                parsed_transfer = provider.parse_erc20_transfer(transfer_data)

                # Get or create token
                token = await self._get_or_create_token(
                    chain_id=wallet_address.chain_id,
                    contract_address=parsed_transfer["contract_address"],
                    symbol=parsed_transfer["token_symbol"],
                    name=parsed_transfer["token_name"],
                    decimals=parsed_transfer["token_decimals"],
                )

                # Determine transaction type
                tx_type = self._determine_transaction_type(parsed_transfer, wallet_address.address_lowercase)

                # Create transaction record
                transaction = Transaction(
                    wallet_id=wallet_address.wallet_id,
                    chain_id=wallet_address.chain_id,
                    token_id=token.id,
                    transaction_hash=parsed_transfer["hash"],
                    block_number=parsed_transfer["block_number"],
                    transaction_index=parsed_transfer["transaction_index"],
                    transaction_type=tx_type.value,
                    status=TransactionStatus.CONFIRMED.value,
                    counterparty_address=parsed_transfer["to_address"]
                    if tx_type in (TransactionType.TRANSFER_OUT, TransactionType.SELL)
                    else parsed_transfer["from_address"],
                    amount=parsed_transfer["value"],
                    gas_used=parsed_transfer["gas_used"],
                    gas_price=parsed_transfer["gas_price"],
                    fee_value=Decimal(parsed_transfer["gas_used"]) * parsed_transfer["gas_price"] / Decimal(10**18),
                    fee_currency="USD",
                    block_timestamp=parsed_transfer["timestamp"],
                    timestamp=parsed_transfer["timestamp"],
                )

                await transaction.save(self.session)

                # Process balance if requested
                if process_balances and transaction.status == TransactionStatus.CONFIRMED.value:
                    balance_manager = BalanceManager(self.session, self.settings)
                    await balance_manager.process_transaction(transaction=transaction, create_snapshot=True)

                synced_count += 1
                logger.debug(f"Created ERC20 transfer {transaction.transaction_hash}")

            except Exception as e:
                logger.error(f"Error processing ERC20 transfer {transfer_data.get('hash')}: {e}")
                # Continue with next transfer instead of failing entire sync
                continue

        return synced_count

    async def _transaction_exists(self, tx_hash: str, chain_id: int) -> bool:
        """Check if a transaction already exists in the database."""
        stmt = (
            select(Transaction)
            .where(Transaction.transaction_hash == tx_hash, Transaction.chain_id == chain_id)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _get_native_token(self, chain_id: int) -> Token:
        """Get the native token for a chain."""
        result = await self.session.execute(
            select(Token).where(Token.chain_id == chain_id, Token.is_native.is_(True)).limit(1)
        )
        token = result.scalar_one_or_none()

        if not token:
            raise ValueError(f"Native token not found for chain {chain_id}")

        return token

    async def _get_or_create_token(
        self, chain_id: int, contract_address: str, symbol: str, name: str, decimals: int
    ) -> Token:
        """Get existing token or create a new one."""
        # Try to find existing token by contract address
        result = await self.session.execute(
            select(Token).where(
                Token.chain_id == chain_id, Token.contract_address_lowercase == contract_address.lower()
            )
        )
        token = result.scalar_one_or_none()

        if token:
            return token

        # Create new token
        logger.info(f"Creating new token: {symbol} ({contract_address}) on chain {chain_id}")

        token_manager = TokenManager(self.session, self.settings)
        token = await token_manager.create(
            {
                "chain_id": chain_id,
                "contract_address": contract_address,
                "contract_address_lowercase": contract_address.lower(),
                "symbol": symbol.upper(),
                "name": name,
                "decimals": decimals,
                "is_native": False,
                "token_standard": "ERC20",
            }
        )

        return token

    @staticmethod
    def _determine_transaction_type(tx_data: dict, wallet_address: str) -> TransactionType:
        """
        Determine transaction type based on from/to addresses.

        Args:
            tx_data: Parsed transaction data
            wallet_address: The wallet address (lowercase)

        Returns:
            TransactionType enum
        """
        from_address = tx_data["from_address"].lower()
        to_address = tx_data["to_address"].lower()

        # Incoming transaction
        if to_address == wallet_address:
            return TransactionType.TRANSFER_IN

        # Outgoing transaction
        if from_address == wallet_address:
            return TransactionType.TRANSFER_OUT

        # Should not happen, but default to TRANSFER_IN
        logger.warning(f"Transaction {tx_data.get('hash')} doesn't match wallet address {wallet_address}")
        return TransactionType.TRANSFER_IN

    @staticmethod
    def _map_chain_to_etherscan(chain: Chain) -> EtherscanChain:
        """
        Map Chain model to EtherscanChain enum.

        Args:
            chain: Chain model instance

        Returns:
            EtherscanChain enum value

        Raises:
            ValueError: If chain is not supported
        """
        # Map by chain name or chain_id
        chain_mapping = {
            "eth-mainnet": EtherscanChain.ETHEREUM,
            "ethereum": EtherscanChain.ETHEREUM,
            "1": EtherscanChain.ETHEREUM,
            "bsc-mainnet": EtherscanChain.BSC,
            "bsc": EtherscanChain.BSC,
            "56": EtherscanChain.BSC,
            "polygon-mainnet": EtherscanChain.POLYGON,
            "polygon": EtherscanChain.POLYGON,
            "137": EtherscanChain.POLYGON,
            "arbitrum-mainnet": EtherscanChain.ARBITRUM,
            "arbitrum": EtherscanChain.ARBITRUM,
            "42161": EtherscanChain.ARBITRUM,
            "optimism-mainnet": EtherscanChain.OPTIMISM,
            "optimism": EtherscanChain.OPTIMISM,
            "10": EtherscanChain.OPTIMISM,
            "base-mainnet": EtherscanChain.BASE,
            "base": EtherscanChain.BASE,
            "8453": EtherscanChain.BASE,
        }

        # Try to match by name first, then by chain_id
        key = chain.name.lower()
        if key in chain_mapping:
            return chain_mapping[key]

        if chain.chain_id and str(chain.chain_id) in chain_mapping:
            return chain_mapping[str(chain.chain_id)]

        raise ValueError(f"Unsupported chain for Etherscan sync: {chain.name} (chain_id: {chain.chain_id})")
