"""
Tests for UserManager.

Tests user-specific functionality:
- create_user()
- get_user()
- get_user_by_email()
- update_user()
- patch_user()
- Password hashing
- Duplicate username/email validation
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.errors import DatabaseError, UserError
from backend.managers.users import UserManager
from backend.schemas import UserCreateOrUpdate, UserPatch, UserSignUp
from backend.security import verify_password
from backend.settings import get_settings


@pytest.mark.asyncio
class TestUserManagerCreateUser:
    """Test user creation functionality."""

    async def test_create_user_success(self, async_session: AsyncSession):
        """Test successful user creation."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user_data = UserSignUp(username="newuser", email="newuser@example.com", password="securepassword123")

        created = await manager.create_user(user_data)

        assert created.id is not None
        assert created.username == "newuser"
        assert created.email == "newuser@example.com"
        assert created.password_hash != "securepassword123"  # Should be hashed
        assert verify_password("securepassword123", created.password_hash)

    async def test_create_user_hashes_password(self, async_session: AsyncSession):
        """Test password is properly hashed."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user_data = UserSignUp(username="user1", email="user1@example.com", password="mypassword")

        created = await manager.create_user(user_data)

        # Password should be hashed, not stored in plain text
        assert created.password_hash != "mypassword"
        # Should verify correctly
        assert verify_password("mypassword", created.password_hash)
        # Wrong password should not verify
        assert not verify_password("wrongpassword", created.password_hash)

    async def test_create_user_duplicate_username(self, async_session: AsyncSession, user_factory):
        """Test creating user with duplicate username fails."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        # Create first user
        existing = user_factory(username="duplicate")
        await existing.save(async_session)

        # Try to create second user with same username
        user_data = UserSignUp(username="duplicate", email="different@example.com", password="password123")

        with pytest.raises(UserError) as exc_info:
            await manager.create_user(user_data)

        assert exc_info.value.status_code == 400

    async def test_create_user_duplicate_email(self, async_session: AsyncSession, user_factory):
        """Test creating user with duplicate email fails."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        # Create first user
        existing = user_factory(email="duplicate@example.com")
        await existing.save(async_session)

        # Try to create second user with same email
        user_data = UserSignUp(username="different", email="duplicate@example.com", password="password123")

        with pytest.raises(UserError) as exc_info:
            await manager.create_user(user_data)

        assert exc_info.value.status_code == 400

    async def test_create_user_ignores_deleted_duplicates(self, async_session: AsyncSession, user_factory):
        """Test can create user with same username as deleted user."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        # Create and delete user
        old_user = user_factory(username="reusable", email="old@example.com")
        await old_user.save(async_session)
        await old_user.delete(async_session)

        # Should be able to create new user with same username
        user_data = UserSignUp(username="reusable", email="new@example.com", password="password123")

        created = await manager.create_user(user_data)

        assert created.username == "reusable"
        assert created.email == "new@example.com"
        assert created.id != old_user.id  # Different user


@pytest.mark.asyncio
class TestUserManagerGetUser:
    """Test user retrieval functionality."""

    async def test_get_user_by_username(self, async_session: AsyncSession, user_factory):
        """Test get_user with username."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user = user_factory(username="findme")
        await user.save(async_session)

        found = await manager.get_user("findme")

        assert found.id == user.id
        assert found.username == "findme"

    async def test_get_user_by_uuid(self, async_session: AsyncSession, user_factory):
        """Test get_user with UUID."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        found = await manager.get_user(str(user.uuid))

        assert found.id == user.id
        assert found.uuid == user.uuid

    async def test_get_user_not_found(self, async_session: AsyncSession):
        """Test get_user raises error when not found."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        with pytest.raises(DatabaseError) as exc_info:
            await manager.get_user("doesnotexist")

        assert exc_info.value.status_code == 404

    async def test_get_user_by_email(self, async_session: AsyncSession, user_factory):
        """Test get_user_by_email."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user = user_factory(email="findme@example.com")
        await user.save(async_session)

        found = await manager.get_user_by_email("findme@example.com")

        assert found.id == user.id
        assert found.email == "findme@example.com"

    async def test_get_user_by_email_not_found(self, async_session: AsyncSession):
        """Test get_user_by_email raises error when not found."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        with pytest.raises(UserError) as exc_info:
            await manager.get_user_by_email("doesnotexist@example.com")

        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
class TestUserManagerUpdateUser:
    """Test user update functionality."""

    async def test_update_user_by_username(self, async_session: AsyncSession, user_factory):
        """Test update_user with username."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user = user_factory(username="oldname", email="old@example.com")
        await user.save(async_session)

        update_data = UserCreateOrUpdate(
            username="newname", email="new@example.com"
        )

        updated = await manager.update_user("oldname", update_data)

        assert updated.id == user.id
        assert updated.username == "newname"
        assert updated.email == "new@example.com"

    async def test_update_user_by_uuid(self, async_session: AsyncSession, user_factory):
        """Test update_user with UUID."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user = user_factory(username="user1", email="user1@example.com")
        await user.save(async_session)

        update_data = UserCreateOrUpdate(username="user1", email="updated@example.com")

        updated = await manager.update_user(str(user.uuid), update_data)

        assert updated.uuid == user.uuid
        assert updated.email == "updated@example.com"

    async def test_update_user_requires_username(self, async_session: AsyncSession, user_factory):
        """Test update_user requires username in data."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        # Try to update without username
        update_data = UserCreateOrUpdate(username=None, email="new@example.com")

        with pytest.raises(UserError) as exc_info:
            await manager.update_user(str(user.uuid), update_data)

        assert exc_info.value.status_code == 400

    async def test_patch_user_partial_update(self, async_session: AsyncSession, user_factory):
        """Test patch_user for partial updates."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user = user_factory(username="original", email="original@example.com")
        await user.save(async_session)

        # Only update email
        patch_data = UserPatch(email="patched@example.com")

        patched = await manager.patch_user(user.username, patch_data)

        # Username should remain
        assert patched.username == "original"
        # Email should be updated
        assert patched.email == "patched@example.com"

    async def test_patch_user_by_uuid(self, async_session: AsyncSession, user_factory):
        """Test patch_user with UUID."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user = user_factory(username="user1")
        await user.save(async_session)

        patch_data = UserPatch(username="updated")

        patched = await manager.patch_user(str(user.uuid), patch_data)

        assert patched.uuid == user.uuid
        assert patched.username == "updated"


@pytest.mark.asyncio
class TestUserManagerEagerLoading:
    """Test user manager eager loading."""

    async def test_get_user_loads_relationships(
        self, async_session: AsyncSession, user_factory, wallet_factory, portfolio_factory
    ):
        """Test get_user eager loads wallets and portfolios."""
        settings = get_settings()
        manager = UserManager(async_session, settings)

        user = user_factory()
        await user.save(async_session)

        wallet = wallet_factory(user.id)
        await wallet.save(async_session)

        portfolio = portfolio_factory(user.id)
        await portfolio.save(async_session)

        # Get user (should eager load relationships)
        found = await manager.get_user(user.username)

        # Should have wallets loaded
        assert hasattr(found, "wallets")
        assert len(found.wallets) > 0

        # Should have portfolios loaded
        assert hasattr(found, "portfolios")
        assert len(found.portfolios) > 0
