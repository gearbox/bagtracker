from loguru import logger

from backend import schemas
from backend.databases.models import CexAccount, Transaction, Wallet
from backend.errors import BadRequestException
from backend.managers import BalanceManager
from backend.managers.base_crud import BaseCRUDManager
from backend.schemas import SnapshotType, TransactionStatus
from backend.services import BalanceCalculator
from backend.validators import get_uuid_or_rise


class TransactionManager(BaseCRUDManager[Transaction]):
    """
    Best practice: never modify past transactions.
    If you need corrections, insert a reversing tx + new tx.
    All inserts must be idempotent (re-running job yields same result).
    Wrap updates in DB transactions.
    For corrections: recompute from earliest affected tx forward.
    """

    # Define relationships to eager load
    eager_load = [
        "wallet",
        "chain",
        "token",
    ]

    @property
    def _model_class(self) -> type[Transaction]:
        return Transaction

    async def create_tx(
        self, transaction_data: schemas.TransactionCreateOrUpdate, process_balance: bool = True
    ) -> Transaction:
        """
        Creates a transaction and optionally processes balance updates.

        Args:
            transaction_data: Transaction data from API
            process_balance: Whether to update balances (default: True)

        Returns:
            Created Transaction object
        """
        transaction_dict = transaction_data.model_dump(exclude_unset=True)
        if transaction_data.wallet_uuid and not transaction_data.cex_account_uuid:
            wallet = await Wallet.get_by_uuid(self.db, transaction_data.wallet_uuid)
            transaction_dict["wallet_id"] = wallet.id
        elif transaction_data.cex_account_uuid and not transaction_data.wallet_uuid:
            cex_account = await CexAccount.get_by_uuid(self.db, transaction_data.cex_account_uuid)
            transaction_dict["cex_account_id"] = cex_account.id
        else:
            raise BadRequestException()

        transaction = await self.create(transaction_dict)

        if process_balance and transaction.status == TransactionStatus.CONFIRMED.value:
            balance_manager = BalanceManager(self.db, self.settings)
            await balance_manager.process_transaction(transaction=transaction, create_snapshot=True)

        return transaction

    async def get_by_wallet_uuid(self, wallet_uuid: str):
        """Gets all transactions for a wallet by UUID."""
        wallet = await Wallet.get_by_uuid(self.db, get_uuid_or_rise(wallet_uuid))
        return await self.get_all(wallet_id=wallet.id)

    async def update_tx(
        self, obj_id: int | str, obj_data: schemas.TransactionCreateOrUpdate, recalculate_balance: bool = False
    ) -> Transaction:
        """
        Updates a transaction.

        WARNING: Updating past transactions can cause balance inconsistencies!
        Best practice: Instead of updating, create a reversing transaction + new transaction.

        Args:
            obj_id: Transaction UUID
            obj_data: New transaction data
            recalculate_balance: If True, recalculates balance from scratch (expensive!)

        Returns:
            Updated Transaction
        """
        # Get existing transaction
        transaction = await self.get(obj_id)

        # Update transaction
        updated_dict = obj_data.model_dump(exclude_unset=True)
        updated_tx = await transaction.update(self.db, updated_dict)

        # If recalculate requested, recalculate balance from all transactions
        if recalculate_balance and updated_tx.wallet_id:
            balance_manager = BalanceManager(self.db, self.settings)
            logger.debug("Recalculating balance")
            await balance_manager.recalculate_wallet_balances(wallet_id=updated_tx.wallet_id, create_snapshots=True)

        return updated_tx

    async def delete_tx(self, obj_uuid: str, recalculate_balance: bool = True) -> None:
        """
        Deletes a transaction.

        WARNING: This should rarely be used! Better to mark as cancelled.

        Args:
            obj_uuid: Transaction UUID
            recalculate_balance: If True, recalculates balance after deletion
        """
        transaction = await self.get(obj_uuid)
        wallet_id = transaction.wallet_id
        token_id = transaction.token_id
        chain_id = transaction.chain_id

        # Delete transaction
        await transaction.delete(self.db)

        # Recalculate balance for this token (if balance still needed)
        if recalculate_balance and wallet_id and token_id and chain_id:
            calculator = BalanceCalculator(self.db, self.settings)
            # This will delete the balance if no transactions remain
            await calculator.recalculate_balance_from_transactions(
                wallet_id=wallet_id, token_id=token_id, chain_id=chain_id
            )

    async def mark_as_cancelled(self, transaction_id: str) -> Transaction:
        """
        Marks a transaction as cancelled (preferred over deletion).
        Recalculates balance to remove this transaction's effects.
        """
        transaction = await self.get(transaction_id)

        # Update status using enum
        transaction.status = TransactionStatus.CANCELLED.value
        await self.db.flush()

        # Recalculate balance to remove this transaction's effects
        if transaction.wallet_id and transaction.token_id and transaction.chain_id:
            calculator = BalanceCalculator(self.db, self.settings)
            # This will handle the case where no confirmed transactions remain
            await calculator.recalculate_balance_from_transactions(
                wallet_id=transaction.wallet_id, token_id=transaction.token_id, chain_id=transaction.chain_id
            )

        return transaction

    async def bulk_create_transactions(
        self, transactions: list[schemas.TransactionCreateOrUpdate], process_balances: bool = True
    ) -> list[Transaction]:
        """
        Efficiently creates multiple transactions at once.
        Used for blockchain sync or CEX API imports.

        Args:
            transactions: List of transaction data
            process_balances: Whether to update balances

        Returns:
            List of created Transaction objects
        """
        created_transactions = []

        # Group transactions by wallet and token for efficient processing
        transactions_by_key = {}

        for tx_data in transactions:
            # Create transaction
            tx = await self.create_tx(tx_data, process_balance=False)
            created_transactions.append(tx)

            # Group for batch balance processing
            if tx.wallet_id:
                key = (tx.wallet_id, tx.token_id, tx.chain_id)
                if key not in transactions_by_key:
                    transactions_by_key[key] = []
                transactions_by_key[key].append(tx)

        # Batch process balances
        if process_balances:
            calculator = BalanceCalculator(self.db, self.settings)

            for wallet_id, token_id, chain_id in transactions_by_key:
                # Recalculate balance from all transactions for this token
                balance = await calculator.recalculate_balance_from_transactions(
                    wallet_id=wallet_id, token_id=token_id, chain_id=chain_id
                )

                # Create a single snapshot after bulk import (if balance exists)
                if balance:
                    await calculator._create_history_snapshot(
                        balance=balance, snapshot_type=SnapshotType.TRANSACTION, triggered_by="bulk_import"
                    )

        return created_transactions
