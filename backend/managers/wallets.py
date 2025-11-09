from uuid import UUID

from backend.databases.models import Wallet, WalletAddress
from backend.errors import DatabaseError
from backend.managers import BaseCRUDManager, WalletAddressManager
from backend.schemas import WalletAddChain, WalletAddressCreate, WalletCreateMultichain


class WalletManager(BaseCRUDManager[Wallet]):
    # Define relationships to eager load
    eager_load = [
        "addresses.chain",  # Load addresses with their chains
        "transactions",  # Load all transactions
        "balances",  # Load current balances
        "portfolio",  # Load portfolio if exists
    ]

    @property
    def _model_class(self) -> type[Wallet]:
        return Wallet

    async def create_multichain_wallet(self, wallet_data: WalletCreateMultichain, username: str) -> Wallet:
        """
        Create a new multichain wallet with multiple addresses.

        Args:
            wallet_data: Wallet creation data with addresses
            username: User identifier

        Returns:
            Created Wallet with addresses
        """
        address_manager = WalletAddressManager(self.db, self.settings)

        for _ in wallet_data.addresses:
            if await address_manager.get_by_address_and_chain(_.address, _.chain_id):
                raise DatabaseError(400, f"Duplicate address error, '{_.address}' is already in use")

        # Create base wallet
        wallet_dict = wallet_data.model_dump(exclude={"addresses"})
        user = await self.get_user_by_name_or_uuid(username)
        user_id = user.id
        wallet_dict["user_id"] = user_id
        wallet = await self.create(wallet_dict, user_id)

        # Add all addresses
        for addr_data in wallet_data.addresses:
            await address_manager.add_chain_to_wallet(wallet_id=wallet.id, address_data=addr_data)

        # Expunge the wallet from session to clear its cached state, then load it with all eager-loaded relationships
        self.db.expunge(wallet)
        return await self.get(wallet.uuid)

    async def add_chain(self, wallet_id: int | UUID, chain_data: WalletAddChain) -> WalletAddress:
        """Add a new chain to existing wallet."""
        if isinstance(wallet_id, UUID):
            wallet = await self.get(wallet_id)
            wallet_id = wallet.id

        address_manager = WalletAddressManager(self.db, self.settings)
        address_data = WalletAddressCreate(**chain_data.model_dump())

        return await address_manager.add_chain_to_wallet(wallet_id=wallet_id, address_data=address_data)

    async def remove_chain(self, wallet_id: int | UUID, chain_id: int) -> None:
        """
        Remove a chain from wallet.
        Actually deactivates rather than deletes to preserve history.
        """
        if isinstance(wallet_id, UUID):
            wallet = await self.get(wallet_id)
            wallet_id = wallet.id

        address_manager = WalletAddressManager(self.db, self.settings)
        await address_manager.deactivate_chain(wallet_id, chain_id)

    async def get_by_address(self, address: str) -> Wallet | None:
        address_manager = WalletAddressManager(self.db, self.settings)
        wallet_address = await address_manager.get_one(address_lowercase=address.lower())
        return await self.get(wallet_address.wallet.id) if wallet_address else None

    async def get_by_address_and_chain(self, address: str, chain_id: int) -> Wallet | None:
        """Find wallet by address on specific chain."""
        address_manager = WalletAddressManager(self.db, self.settings)
        wallet_address = await address_manager.get_by_address_and_chain(address, chain_id)

        return await self.get(wallet_address.wallet.id) if wallet_address else None
