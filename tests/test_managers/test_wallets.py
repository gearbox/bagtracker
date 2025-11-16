"""
Tests for WalletManager.

Tests wallet-specific functionality:
- create_multichain_wallet()
- add_chain()
- remove_chain()
- get_by_address()
- get_by_address_and_chain()
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.errors import DatabaseError
from backend.managers.wallets import WalletManager
from backend.schemas import WalletAddChain, WalletAddressCreate, WalletCreateMultichain, WalletType
from backend.settings import get_settings


@pytest.mark.asyncio
class TestWalletManagerCreate:
    """Test wallet creation functionality."""

    async def test_create_multichain_wallet(self, async_session: AsyncSession, user_factory, chain_factory):
        """Test creating multichain wallet with addresses."""
        settings = get_settings()
        manager = WalletManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        chain1 = chain_factory(chain_id=1, name="Ethereum")
        chain2 = chain_factory(chain_id=137, name="Polygon")
        await chain1.save(async_session)
        await chain2.save(async_session)

        wallet_data = WalletCreateMultichain(
            wallet_type=WalletType.METAMASK,
            name="My Wallet",
            addresses=[
                WalletAddressCreate(chain_id=chain1.id, address="0xabc123"),
                WalletAddressCreate(chain_id=chain2.id, address="0xdef456"),
            ],
        )

        created = await manager.create_multichain_wallet(wallet_data, user.username)

        assert created.id is not None
        assert created.user_id == user.id
        assert created.wallet_type == "metamask"
        assert created.name == "My Wallet"
        assert len(created.addresses) == 2

        # Check addresses
        addresses_by_chain = {addr.chain_id: addr for addr in created.addresses}
        assert chain1.id in addresses_by_chain
        assert chain2.id in addresses_by_chain
        assert addresses_by_chain[chain1.id].address == "0xabc123"
        assert addresses_by_chain[chain2.id].address == "0xdef456"

    async def test_create_multichain_wallet_duplicate_address(
        self, async_session: AsyncSession, user_factory, chain_factory, wallet_factory, wallet_address_factory
    ):
        """Test creating wallet with duplicate address fails."""
        settings = get_settings()
        manager = WalletManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        chain = chain_factory()
        await chain.save(async_session)

        # Create existing wallet with address
        existing_wallet = wallet_factory(user.id)
        await existing_wallet.save(async_session)

        existing_addr = wallet_address_factory(existing_wallet.id, chain.id, address="0xDUPLICATE")
        await existing_addr.save(async_session)

        # Try to create new wallet with same address
        wallet_data = WalletCreateMultichain(
            wallet_type=WalletType.METAMASK, addresses=[WalletAddressCreate(chain_id=chain.id, address="0xDUPLICATE")]
        )

        with pytest.raises(DatabaseError) as exc_info:
            await manager.create_multichain_wallet(wallet_data, user.username)

        assert exc_info.value.status_code == 400


@pytest.mark.asyncio
class TestWalletManagerAddRemoveChain:
    """Test adding/removing chains to wallets."""

    async def test_add_chain_by_wallet_id(
        self, async_session: AsyncSession, user_factory, wallet_factory, chain_factory
    ):
        """Test adding chain to existing wallet by ID."""
        settings = get_settings()
        manager = WalletManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        wallet = wallet_factory(user.id)
        await wallet.save(async_session)

        chain = chain_factory()
        await chain.save(async_session)

        chain_data = WalletAddChain(chain_id=chain.id, address="0xNEWADDRESS")

        added = await manager.add_chain(wallet.id, chain_data)

        assert added.wallet_id == wallet.id
        assert added.chain_id == chain.id
        assert added.address == "0xNEWADDRESS"

    async def test_add_chain_by_wallet_uuid(
        self, async_session: AsyncSession, user_factory, wallet_factory, chain_factory
    ):
        """Test adding chain to existing wallet by UUID."""
        settings = get_settings()
        manager = WalletManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        wallet = wallet_factory(user.id)
        await wallet.save(async_session)

        chain = chain_factory()
        await chain.save(async_session)

        chain_data = WalletAddChain(chain_id=chain.id, address="0xNEWADDRESS")

        added = await manager.add_chain(wallet.uuid, chain_data)

        assert added.wallet_id == wallet.id
        assert added.chain_id == chain.id

    async def test_remove_chain_by_wallet_id(
        self, async_session: AsyncSession, user_factory, wallet_factory, chain_factory, wallet_address_factory
    ):
        """Test removing chain from wallet by ID."""
        settings = get_settings()
        manager = WalletManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        wallet = wallet_factory(user.id)
        await wallet.save(async_session)

        chain = chain_factory()
        await chain.save(async_session)

        address = wallet_address_factory(wallet.id, chain.id)
        await address.save(async_session)

        # Remove chain (actually deactivates)
        await manager.remove_chain(wallet.id, chain.id)

        # Verify address is deactivated
        from backend.databases.models.wallet import WalletAddress

        deactivated = await WalletAddress.get_one(async_session, wallet_id=wallet.id, chain_id=chain.id)
        assert deactivated.is_active is False

    async def test_remove_chain_by_wallet_uuid(
        self, async_session: AsyncSession, user_factory, wallet_factory, chain_factory, wallet_address_factory
    ):
        """Test removing chain from wallet by UUID."""
        settings = get_settings()
        manager = WalletManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        wallet = wallet_factory(user.id)
        await wallet.save(async_session)

        chain = chain_factory()
        await chain.save(async_session)

        address = wallet_address_factory(wallet.id, chain.id)
        await address.save(async_session)

        # Remove chain
        await manager.remove_chain(wallet.uuid, chain.id)

        # Verify address is deactivated
        from backend.databases.models.wallet import WalletAddress

        deactivated = await WalletAddress.get_one(async_session, wallet_id=wallet.id, chain_id=chain.id)
        assert deactivated.is_active is False


@pytest.mark.asyncio
class TestWalletManagerFindByAddress:
    """Test finding wallets by address."""

    async def test_get_by_address(
        self, async_session: AsyncSession, user_factory, wallet_factory, chain_factory, wallet_address_factory
    ):
        """Test finding wallet by address."""
        settings = get_settings()
        manager = WalletManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        wallet = wallet_factory(user.id)
        await wallet.save(async_session)

        chain = chain_factory()
        await chain.save(async_session)

        address = wallet_address_factory(wallet.id, chain.id, address="0xFINDME")
        await address.save(async_session)

        found = await manager.get_by_address("0xFINDME")

        assert found is not None
        assert found.id == wallet.id

    async def test_get_by_address_case_insensitive(
        self, async_session: AsyncSession, user_factory, wallet_factory, chain_factory, wallet_address_factory
    ):
        """Test finding wallet by address is case insensitive."""
        settings = get_settings()
        manager = WalletManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        wallet = wallet_factory(user.id)
        await wallet.save(async_session)

        chain = chain_factory()
        await chain.save(async_session)

        address = wallet_address_factory(wallet.id, chain.id, address="0xAbCdEf")
        await address.save(async_session)

        # Search with different case
        found = await manager.get_by_address("0xABCDEF")

        assert found is not None
        assert found.id == wallet.id

    async def test_get_by_address_and_chain(
        self, async_session: AsyncSession, user_factory, wallet_factory, chain_factory, wallet_address_factory
    ):
        """Test finding wallet by address and specific chain."""
        settings = get_settings()
        manager = WalletManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        wallet = wallet_factory(user.id)
        await wallet.save(async_session)

        chain1 = chain_factory(chain_id=1, name="Ethereum")
        chain2 = chain_factory(chain_id=137, name="Polygon")
        await chain1.save(async_session)
        await chain2.save(async_session)

        # Same wallet, different addresses on different chains
        addr1 = wallet_address_factory(wallet.id, chain1.id, address="0xETH")
        addr2 = wallet_address_factory(wallet.id, chain2.id, address="0xPOLY")
        await addr1.save(async_session)
        await addr2.save(async_session)

        # Find by address and specific chain
        found = await manager.get_by_address_and_chain("0xETH", chain1.id)

        assert found is not None
        assert found.id == wallet.id

    async def test_get_by_address_not_found(self, async_session: AsyncSession):
        """Test get_by_address returns None when not found."""
        settings = get_settings()
        manager = WalletManager(async_session, settings)

        found = await manager.get_by_address("0xDOESNOTEXIST")

        assert found is None

    async def test_get_by_address_and_chain_not_found(self, async_session: AsyncSession, chain_factory):
        """Test get_by_address_and_chain returns None when not found."""
        settings = get_settings()
        manager = WalletManager(async_session, settings)

        chain = chain_factory()
        await chain.save(async_session)

        found = await manager.get_by_address_and_chain("0xDOESNOTEXIST", chain.id)

        assert found is None


@pytest.mark.asyncio
class TestWalletManagerEagerLoading:
    """Test wallet manager eager loading."""

    async def test_get_wallet_loads_relationships(
        self,
        async_session: AsyncSession,
        user_factory,
        wallet_factory,
        chain_factory,
        wallet_address_factory,
        transaction_factory,
        token_factory,
    ):
        """Test get() eager loads addresses, transactions, and balances."""
        settings = get_settings()
        manager = WalletManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        wallet = wallet_factory(user.id)
        await wallet.save(async_session)

        chain = chain_factory()
        await chain.save(async_session)

        address = wallet_address_factory(wallet.id, chain.id)
        await address.save(async_session)

        token = token_factory(chain.id)
        await token.save(async_session)

        transaction = transaction_factory(wallet.id, token.id, chain.id)
        await transaction.save(async_session)

        # Get wallet (should eager load)
        found = await manager.get(wallet.uuid)

        # Addresses should be loaded
        assert hasattr(found, "addresses")
        assert len(found.addresses) > 0
        # Chain should be loaded on address
        assert found.addresses[0].chain is not None

        # Transactions should be loaded
        assert hasattr(found, "transactions")
        assert len(found.transactions) > 0
