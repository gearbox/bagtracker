"""
Tests for BaseCRUDManager.

Tests common CRUD operations that all managers inherit:
- get()
- get_one()
- get_all()
- get_all_by_user()
- create()
- create_from_schema()
- update()
- patch()
- upsert()
- delete()
- eager loading functionality
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.databases.models.portfolio import User
from backend.errors import BadRequestException, DatabaseError
from backend.managers import UserManager, WalletManager
from backend.schemas import UserSignUp, UserCreateOrUpdate, UserPatch
from backend.settings import get_settings
from backend.security import hash_password


@pytest.mark.asyncio
class TestBaseCRUDManager:
    """Test BaseCRUDManager common functionality."""

    async def test_manager_initialization(self, async_session: AsyncSession):
        """Test manager initializes correctly."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        assert manager.db == async_session
        assert manager.settings == settings
        assert manager.model == User

    async def test_get_by_id(self, async_session: AsyncSession, user_factory):
        """Test get() with integer ID."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        found = await manager.get(user.id)

        assert found.id == user.id
        assert found.username == user.username

    async def test_get_by_uuid(self, async_session: AsyncSession, user_factory):
        """Test get() with UUID."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        found = await manager.get(user.uuid)

        assert found.uuid == user.uuid
        assert found.username == user.username

    async def test_get_by_string_uuid(self, async_session: AsyncSession, user_factory):
        """Test get() with string UUID."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        found = await manager.get(str(user.uuid))

        assert found.uuid == user.uuid

    async def test_get_not_found(self, async_session: AsyncSession):
        """Test get() raises error when not found."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        with pytest.raises(DatabaseError) as exc_info:
            await manager.get(999999)
        assert exc_info.value.status_code == 404

    async def test_get_excludes_deleted(self, async_session: AsyncSession, user_factory):
        """Test get() excludes soft-deleted by default."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)
        await user.delete(async_session)

        with pytest.raises(DatabaseError) as exc_info:
            await manager.get(user.id)
        assert exc_info.value.status_code == 404

    async def test_get_include_deleted(self, async_session: AsyncSession, user_factory):
        """Test get() can include deleted records."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)
        await user.delete(async_session)

        found = await manager.get(user.id, include_deleted=True)

        assert found.id == user.id
        assert found.is_deleted is True

    async def test_get_one_by_kwargs(self, async_session: AsyncSession, user_factory):
        """Test get_one() with filter kwargs."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user = user_factory(username="findme")
        await user.save(async_session)

        found = await manager.get_one(username="findme")

        assert found.username == "findme"

    async def test_get_one_not_found(self, async_session: AsyncSession):
        """Test get_one() raises error when not found."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        with pytest.raises(DatabaseError) as exc_info:
            await manager.get_one(username="doesnotexist")
        assert exc_info.value.status_code == 404

    async def test_get_all(self, async_session: AsyncSession, user_factory):
        """Test get_all() retrieves multiple records."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user1 = user_factory(username="user1")
        user2 = user_factory(username="user2")
        user3 = user_factory(username="user3")

        await user1.save(async_session)
        await user2.save(async_session)
        await user3.save(async_session)

        all_users = await manager.get_all()

        assert len(all_users) >= 3
        usernames = [u.username for u in all_users]
        assert "user1" in usernames
        assert "user2" in usernames
        assert "user3" in usernames

    async def test_get_all_with_filter(self, async_session: AsyncSession, user_factory):
        """Test get_all() with filter kwargs."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user1 = user_factory(username="specific")
        user2 = user_factory(username="other")

        await user1.save(async_session)
        await user2.save(async_session)

        users = await manager.get_all(username="specific")

        assert len(users) == 1
        assert users[0].username == "specific"

    async def test_get_all_excludes_deleted(self, async_session: AsyncSession, user_factory):
        """Test get_all() excludes soft-deleted by default."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user1 = user_factory(username="active")
        user2 = user_factory(username="deleted")

        await user1.save(async_session)
        await user2.save(async_session)
        await user2.delete(async_session)

        users = await manager.get_all()
        usernames = [u.username for u in users]

        assert "active" in usernames
        assert "deleted" not in usernames

    async def test_create_from_dict(self, async_session: AsyncSession):
        """Test create() with dictionary."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        create_dict = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password_hash": hash_password("password123"),
        }

        created = await manager.create(create_dict)

        assert created.id is not None
        assert created.username == "newuser"
        assert created.email == "newuser@example.com"

    async def test_create_from_schema(self, async_session: AsyncSession):
        """Test create_from_schema() with Pydantic model."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user_data = UserSignUp(username="schemauser", email="schema@example.com", password="password123")

        # Note: UserManager has create_user which handles password hashing
        # We test create_from_schema directly here
        user_dict = user_data.model_dump(exclude={"password"})
        user_dict["password_hash"] = hash_password(user_data.password)

        schema = UserCreateOrUpdate(**user_dict)
        created = await manager.create_from_schema(schema)

        assert created.username == "schemauser"

    async def test_update(self, async_session: AsyncSession, user_factory):
        """Test update() method."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user = user_factory(username="oldname", email="old@example.com")
        await user.save(async_session)

        update_data = UserCreateOrUpdate(username="newname", email="new@example.com")

        updated = await manager.update(user.uuid, update_data)

        assert updated.id == user.id
        assert updated.username == "newname"
        assert updated.email == "new@example.com"

    async def test_patch(self, async_session: AsyncSession, user_factory):
        """Test patch() method for partial updates."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user = user_factory(username="original", email="original@example.com")
        await user.save(async_session)

        patch_data = UserPatch(email="patched@example.com")

        patched = await manager.patch(user.uuid, patch_data)

        # Username should remain unchanged
        assert patched.username == "original"
        # Email should be updated
        assert patched.email == "patched@example.com"

    async def test_upsert_creates_new(self, async_session: AsyncSession):
        """Test upsert() creates new record when UUID doesn't exist."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        new_uuid = uuid.uuid4()
        user_data = UserSignUp(username="upsertuser", email="upsert@example.com", password="password123")

        user_dict = user_data.model_dump(exclude={"password"})
        user_dict["password_hash"] = hash_password(user_data.password)
        user_dict["uuid"] = new_uuid

        schema = UserCreateOrUpdate(**user_dict)
        upserted = await manager.upsert(schema)

        assert upserted.username == "upsertuser"
        assert upserted.uuid == new_uuid

    async def test_upsert_updates_existing(self, async_session: AsyncSession, user_factory):
        """Test upsert() updates existing record."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user = user_factory(username="original")
        await user.save(async_session)

        upsert_data = UserCreateOrUpdate(
            username="updated", email="updated@example.com"
        )

        upserted = await manager.upsert(upsert_data, for_username_or_id=user.uuid)

        assert upserted.id == user.id
        assert upserted.uuid == user.uuid
        assert upserted.username == "updated"

    async def test_delete(self, async_session: AsyncSession, user_factory):
        """Test delete() soft deletes record."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        await manager.delete(user.uuid)

        # Should raise error when trying to get (excludes deleted)
        with pytest.raises(DatabaseError):
            await manager.get(user.uuid)

        # But should exist when including deleted
        found = await manager.get(user.uuid, include_deleted=True)
        assert found.is_deleted is True


@pytest.mark.asyncio
class TestBaseCRUDManagerEagerLoading:
    """Test eager loading functionality."""

    async def test_eager_load_relationships(self, async_session: AsyncSession, user_factory, wallet_factory):
        """Test eager loading loads relationships."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        # Create user with wallet
        user = user_factory()
        await user.save(async_session)

        wallet = wallet_factory(user.id)
        await wallet.save(async_session)

        # UserManager has eager_load = ["wallets.addresses.chain", "portfolios.wallets", "cex_accounts"]
        found = await manager.get(user.uuid)

        # Wallets should be loaded (not trigger additional query)
        assert hasattr(found, "wallets")
        # The wallet collection should be accessible without triggering lazy load
        assert len(found.wallets) > 0

    async def test_custom_eager_load(self, async_session: AsyncSession, user_factory):
        """Test custom eager loading override."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        # Test with custom eager load
        found = await manager.get(user.uuid, eager_load=["wallets"])

        assert found.uuid == user.uuid


@pytest.mark.asyncio
class TestBaseCRUDManagerUserHelpers:
    """Test user-related helper methods."""

    async def test_get_user_by_name_or_uuid_with_username(self, async_session: AsyncSession, user_factory):
        """Test get_user_by_name_or_uuid with username."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user = user_factory(username="testuser")
        await user.save(async_session)

        found = await manager.get_user_by_name_or_uuid("testuser")

        assert found.username == "testuser"

    async def test_get_user_by_name_or_uuid_with_uuid(self, async_session: AsyncSession, user_factory):
        """Test get_user_by_name_or_uuid with UUID."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        found = await manager.get_user_by_name_or_uuid(str(user.uuid))

        assert found.uuid == user.uuid

    async def test_get_all_by_user(self, async_session: AsyncSession, user_factory, wallet_factory):
        """Test get_all_by_user retrieves user's records."""
        settings = get_settings()

        # Use WalletManager for this test
        wallet_manager = WalletManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        wallet1 = wallet_factory(user.id)
        wallet2 = wallet_factory(user.id)
        await wallet1.save(async_session)
        await wallet2.save(async_session)

        # Get all wallets for this user
        wallets = await wallet_manager.get_all_by_user(user.username)

        assert len(wallets) == 2
        assert all(w.user_id == user.id for w in wallets)
