from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.databases.models import WalletAddress
from backend.errors import WalletError
from backend.managers import BaseCRUDManager
from backend.schemas import WalletAddressCreate


class WalletAddressManager(BaseCRUDManager[WalletAddress]):
    """Manager for wallet addresses."""

    eager_load = ["chain", "wallet"]

    @property
    def _model_class(self) -> type[WalletAddress]:
        return WalletAddress

    async def add_chain_to_wallet(self, wallet_id: int, address_data: WalletAddressCreate) -> WalletAddress:
        """
        Add a new chain to an existing wallet.

        Args:
            wallet_id: Wallet ID
            address_data: Address information for the new chain
        """
        # Check if address already exists on this chain
        existing = await self.db.scalar(
            select(WalletAddress).filter(
                WalletAddress.wallet_id == wallet_id, WalletAddress.chain_id == address_data.chain_id
            )
        )

        if existing:
            raise WalletError(400, f"Wallet already has an address on chain {address_data.chain_id}")

        # Create new address
        data = address_data.model_dump()
        data["wallet_id"] = wallet_id
        data["address_lowercase"] = data["address"].lower()

        return await self.create(data)

    async def get_wallet_addresses(self, wallet_id: int, include_inactive: bool = False) -> list[WalletAddress]:
        """Get all addresses for a wallet."""
        stmt = (
            select(WalletAddress)
            .filter(WalletAddress.wallet_id == wallet_id)
            .options(selectinload(WalletAddress.chain))
        )

        if not include_inactive:
            stmt = stmt.filter(WalletAddress.is_active.is_(True))

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_address_and_chain(self, address: str, chain_id: int) -> WalletAddress | None:
        """Find wallet address by address and chain."""
        stmt = (
            select(WalletAddress)
            .filter(WalletAddress.address_lowercase == address.lower(), WalletAddress.chain_id == chain_id)
            .options(selectinload(WalletAddress.wallet), selectinload(WalletAddress.chain))
        )

        return await self.db.scalar(stmt)

    async def deactivate_chain(self, wallet_id: int, chain_id: int) -> WalletAddress:
        """
        Deactivate a chain for a wallet.
        Doesn't delete - preserves transaction history.
        """
        stmt = select(WalletAddress).filter(WalletAddress.wallet_id == wallet_id, WalletAddress.chain_id == chain_id)

        wallet_address = await self.db.scalar(stmt)
        if not wallet_address:
            raise WalletError(404, f"Address not found for chain {chain_id}")

        return await wallet_address.update(self.db, {"is_active": False})
