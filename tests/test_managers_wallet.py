"""Tests for WalletManager"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.databases.models import Chain, User, Wallet
from backend.errors import DatabaseError
from backend.managers import WalletManager
from backend.schemas import WalletAddChain, WalletAddressCreate, WalletCreateMultichain, WalletType


@pytest.mark.asyncio
class TestWalletManager:
    """Test WalletManager CRUD operations"""

    async def test_create_multichain_wallet(
        self, wallet_manager: WalletManager, test_user: User, test_chain: Chain, test_chain_bsc: Chain
    ):
        """Test creating a multichain wallet"""
        wallet_data = WalletCreateMultichain(
            wallet_type=WalletType.METAMASK,
            sync_enabled=True,
            addresses=[
                WalletAddressCreate(
                    chain_id=test_chain.id, address="0x1234567890123456789012345678901234567890"
                ),
                WalletAddressCreate(chain_id=test_chain_bsc.id, address="0x0987654321098765432109876543210987654321"),
            ],
        )

        wallet = await wallet_manager.create_multichain_wallet(wallet_data, test_user.username)

        assert wallet.id is not None
        assert wallet.user_id == test_user.id
        assert wallet.wallet_type == WalletType.METAMASK.value
        assert len(wallet.addresses) == 2

        # Check addresses
        chain_ids = {addr.chain_id for addr in wallet.addresses}
        assert test_chain.id in chain_ids
        assert test_chain_bsc.id in chain_ids

    async def test_create_multichain_wallet_duplicate_address(
        self, wallet_manager: WalletManager, test_user: User, test_wallet: Wallet, test_chain: Chain
    ):
        """Test creating wallet with duplicate address raises error"""
        # Get existing address from test_wallet
        existing_address = test_wallet.addresses[0].address

        wallet_data = WalletCreateMultichain(
            wallet_type=WalletType.METAMASK,
            sync_enabled=True,
            addresses=[
                WalletAddressCreate(chain_id=test_chain.id, address=existing_address),
            ],
        )

        with pytest.raises(DatabaseError) as exc_info:
            await wallet_manager.create_multichain_wallet(wallet_data, test_user.username)

        assert exc_info.value.status_code == 400
        assert "duplicate" in exc_info.value.exception_message.lower()

    async def test_get_wallet_by_uuid(self, wallet_manager: WalletManager, test_wallet: Wallet):
        """Test getting wallet by UUID"""
        wallet = await wallet_manager.get(test_wallet.uuid)

        assert wallet.id == test_wallet.id
        assert wallet.uuid == test_wallet.uuid
        assert wallet.user_id == test_wallet.user_id

    async def test_get_wallet_not_found(self, wallet_manager: WalletManager):
        """Test getting non-existent wallet raises error"""
        import uuid

        fake_uuid = uuid.uuid4()

        with pytest.raises(DatabaseError) as exc_info:
            await wallet_manager.get(fake_uuid)

        assert exc_info.value.status_code == 404

    async def test_get_all_by_user(self, wallet_manager: WalletManager, test_user: User, test_wallet: Wallet):
        """Test getting all wallets for a user"""
        wallets = await wallet_manager.get_all_by_user(test_user.username)

        assert len(wallets) >= 1
        wallet_ids = [w.id for w in wallets]
        assert test_wallet.id in wallet_ids

    async def test_add_chain_to_wallet(
        self, wallet_manager: WalletManager, test_wallet: Wallet, test_chain_bsc: Chain
    ):
        """Test adding a chain to existing wallet"""
        chain_data = WalletAddChain(
            chain_id=test_chain_bsc.id, address="0x9999999999999999999999999999999999999999"
        )

        address = await wallet_manager.add_chain(test_wallet.uuid, chain_data)

        assert address.wallet_id == test_wallet.id
        assert address.chain_id == test_chain_bsc.id
        assert address.address == "0x9999999999999999999999999999999999999999"

    async def test_remove_chain_from_wallet(
        self, wallet_manager: WalletManager, test_wallet: Wallet, test_chain: Chain
    ):
        """Test removing a chain from wallet (soft delete)"""
        await wallet_manager.remove_chain(test_wallet.uuid, test_chain.id)

        # Refresh wallet to see changes
        wallet = await wallet_manager.get(test_wallet.uuid)

        # Address should be soft-deleted (not active)
        active_addresses = [addr for addr in wallet.addresses if not addr.is_deleted]
        chain_ids = [addr.chain_id for addr in active_addresses]
        assert test_chain.id not in chain_ids

    async def test_get_by_address(
        self, wallet_manager: WalletManager, test_wallet: Wallet, async_session: AsyncSession
    ):
        """Test finding wallet by address"""
        address_str = test_wallet.addresses[0].address

        wallet = await wallet_manager.get_by_address(address_str)

        assert wallet is not None
        assert wallet.id == test_wallet.id

    async def test_get_by_address_and_chain(
        self, wallet_manager: WalletManager, test_wallet: Wallet, test_chain: Chain
    ):
        """Test finding wallet by address and chain"""
        address_str = test_wallet.addresses[0].address

        wallet = await wallet_manager.get_by_address_and_chain(address_str, test_chain.id)

        assert wallet is not None
        assert wallet.id == test_wallet.id

    async def test_get_by_address_not_found(self, wallet_manager: WalletManager):
        """Test finding wallet by non-existent address returns None"""
        wallet = await wallet_manager.get_by_address("0x0000000000000000000000000000000000000000")

        assert wallet is None

    async def test_delete_wallet(self, wallet_manager: WalletManager, test_wallet: Wallet):
        """Test soft deleting wallet"""
        await wallet_manager.delete(test_wallet.uuid)

        # Wallet should not be found in normal queries
        with pytest.raises(DatabaseError):
            await wallet_manager.get(test_wallet.uuid)

        # But should be found when including deleted
        deleted_wallet = await Wallet.get_by_id(wallet_manager.db, test_wallet.id, include_deleted=True)
        assert deleted_wallet.is_deleted is True

    async def test_wallet_eager_loading(self, wallet_manager: WalletManager, test_wallet: Wallet):
        """Test that wallet eager loads relationships"""
        wallet = await wallet_manager.get(test_wallet.uuid)

        # Should have addresses loaded
        assert hasattr(wallet, "addresses")
        assert len(wallet.addresses) > 0

        # Addresses should have chains loaded
        for address in wallet.addresses:
            assert hasattr(address, "chain")
            assert address.chain is not None
