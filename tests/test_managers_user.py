"""Tests for UserManager"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.databases.models import User
from backend.errors import DatabaseError, UserError
from backend.managers import UserManager
from backend.schemas import UserPatch, UserSignUp
from backend.security import verify_password


@pytest.mark.asyncio
class TestUserManager:
    """Test UserManager CRUD operations"""

    async def test_create_user(self, user_manager: UserManager, async_session: AsyncSession):
        """Test creating a new user"""
        user_data = UserSignUp(username="newuser", password="SecurePass123!", email="newuser@example.com")

        user = await user_manager.create_user(user_data)

        assert user.id is not None
        assert user.username == "newuser"
        assert user.email == "newuser@example.com"
        assert user.password_hash is not None
        assert verify_password("SecurePass123!", user.password_hash)
        assert user.uuid is not None

    async def test_create_user_duplicate_username(self, user_manager: UserManager, test_user: User):
        """Test creating user with duplicate username raises error"""
        user_data = UserSignUp(username=test_user.username, password="Pass123!", email="different@example.com")

        with pytest.raises(UserError) as exc_info:
            await user_manager.create_user(user_data)

        assert exc_info.value.status_code == 400
        assert "username" in exc_info.value.exception_message.lower()

    async def test_create_user_duplicate_email(self, user_manager: UserManager, test_user: User):
        """Test creating user with duplicate email raises error"""
        user_data = UserSignUp(username="differentuser", password="Pass123!", email=test_user.email)

        with pytest.raises(UserError) as exc_info:
            await user_manager.create_user(user_data)

        assert exc_info.value.status_code == 400
        assert "email" in exc_info.value.exception_message.lower()

    async def test_get_user_by_username(self, user_manager: UserManager, test_user: User):
        """Test getting user by username"""
        user = await user_manager.get_user(test_user.username)

        assert user.id == test_user.id
        assert user.username == test_user.username
        assert user.email == test_user.email

    async def test_get_user_by_uuid(self, user_manager: UserManager, test_user: User):
        """Test getting user by UUID"""
        user = await user_manager.get_user(str(test_user.uuid))

        assert user.id == test_user.id
        assert user.username == test_user.username

    async def test_get_user_not_found(self, user_manager: UserManager):
        """Test getting non-existent user raises error"""
        with pytest.raises(DatabaseError) as exc_info:
            await user_manager.get_user("nonexistent")

        assert exc_info.value.status_code == 404

    async def test_get_user_by_email(self, user_manager: UserManager, test_user: User):
        """Test getting user by email"""
        user = await user_manager.get_user_by_email(test_user.email)

        assert user.id == test_user.id
        assert user.email == test_user.email

    async def test_get_user_by_email_not_found(self, user_manager: UserManager):
        """Test getting user by non-existent email raises error"""
        with pytest.raises(UserError) as exc_info:
            await user_manager.get_user_by_email("nonexistent@example.com")

        assert exc_info.value.status_code == 404

    async def test_patch_user(self, user_manager: UserManager, test_user: User):
        """Test partially updating user"""
        patch_data = UserPatch(email="updated@example.com")

        updated_user = await user_manager.patch_user(test_user.username, patch_data)

        assert updated_user.id == test_user.id
        assert updated_user.email == "updated@example.com"
        assert updated_user.username == test_user.username  # Unchanged

    async def test_delete_user(self, user_manager: UserManager, test_user: User):
        """Test soft deleting user"""
        await user_manager.delete(test_user.uuid)

        # User should not be found in normal queries
        with pytest.raises(DatabaseError):
            await user_manager.get_user(test_user.username)

        # But should be found when including deleted
        deleted_user = await User.get_by_id(user_manager.db, test_user.id, include_deleted=True)
        assert deleted_user.is_deleted is True

    async def test_get_all_users(self, user_manager: UserManager, test_user: User, test_user_2: User):
        """Test getting all users"""
        users = await user_manager.get_all()

        assert len(users) >= 2
        usernames = [u.username for u in users]
        assert test_user.username in usernames
        assert test_user_2.username in usernames

    async def test_get_all_users_excludes_deleted(
        self, user_manager: UserManager, test_user: User, async_session: AsyncSession
    ):
        """Test that get_all excludes soft-deleted users by default"""
        # Delete one user
        await test_user.delete(async_session)

        users = await user_manager.get_all()

        usernames = [u.username for u in users]
        assert test_user.username not in usernames

    async def test_get_all_users_includes_deleted(
        self, user_manager: UserManager, test_user: User, async_session: AsyncSession
    ):
        """Test that get_all can include soft-deleted users"""
        # Delete one user
        await test_user.delete(async_session)

        users = await user_manager.get_all(include_deleted=True)

        usernames = [u.username for u in users]
        assert test_user.username in usernames
