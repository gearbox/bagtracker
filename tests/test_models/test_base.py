"""
Tests for Base model methods.

Tests the common functionality inherited by all models:
- save()
- delete() / delete_hard()
- restore()
- create()
- update()
- upsert()
- get_by_id()
- get_by_uuid()
- get_one()
- get_all()
- to_dict()
- to_json()
"""

import json
import uuid
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.databases.models.portfolio import User
from backend.errors import DatabaseError
from backend.security import hash_password


@pytest.mark.asyncio
class TestBaseModelMethods:
    """Test Base model CRUD methods."""

    async def test_save_new_instance(self, async_session: AsyncSession):
        """Test saving a new model instance."""
        user = User(username="testuser", email="test@example.com", password_hash=hash_password("password123"))

        await user.save(async_session)

        assert user.id is not None
        assert user.uuid is not None
        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.is_deleted is False

    async def test_save_with_by_user_id(self, async_session: AsyncSession):
        """Test saving with audit trail (by_user_id)."""
        creator = User(username="creator", email="creator@example.com", password_hash=hash_password("pass"))
        await creator.save(async_session)

        user = User(username="testuser", email="test@example.com", password_hash=hash_password("pass"))
        await user.save(async_session, by_user_id=creator.id)

        assert user.updated_by == creator.id

    async def test_soft_delete(self, async_session: AsyncSession, user_factory):
        """Test soft delete marks record as deleted."""
        user = user_factory()
        await user.save(async_session)

        await user.delete(async_session)

        assert user.is_deleted is True
        # Should not be found in normal queries
        with pytest.raises(DatabaseError) as exc_info:
            await User.get_by_id(async_session, user.id)
        assert exc_info.value.status_code == 404

        # Should be found when including deleted
        found_user = await User.get_by_id(async_session, user.id, include_deleted=True)
        assert found_user.id == user.id
        assert found_user.is_deleted is True

    async def test_hard_delete(self, async_session: AsyncSession, user_factory):
        """Test hard delete permanently removes record."""
        user = user_factory()
        await user.save(async_session)
        user_id = user.id

        await user.delete_hard(async_session)

        # Should not be found even with include_deleted
        with pytest.raises(DatabaseError):
            await User.get_by_id(async_session, user_id, include_deleted=True)

    async def test_restore(self, async_session: AsyncSession, user_factory):
        """Test restoring a soft-deleted record."""
        user = user_factory()
        await user.save(async_session)
        await user.delete(async_session)

        assert user.is_deleted is True

        await user.restore(async_session)

        assert user.is_deleted is False
        # Should be found in normal queries again
        found_user = await User.get_by_id(async_session, user.id)
        assert found_user.id == user.id

    async def test_create(self, async_session: AsyncSession):
        """Test create method."""
        user = User()
        create_dict = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password_hash": hash_password("password123"),
        }

        created_user = await user.create(async_session, create_dict)

        assert created_user.id is not None
        assert created_user.username == "newuser"
        assert created_user.email == "newuser@example.com"

    async def test_update(self, async_session: AsyncSession, user_factory):
        """Test update method."""
        user = user_factory(username="oldname")
        await user.save(async_session)

        update_dict = {"username": "newname"}
        updated_user = await user.update(async_session, update_dict)

        assert updated_user.username == "newname"
        assert updated_user.id == user.id  # ID should not change

    async def test_upsert_create(self, async_session: AsyncSession):
        """Test upsert creates new record when instance has no ID."""
        user = User()
        upsert_dict = {
            "username": "upsertuser",
            "email": "upsert@example.com",
            "password_hash": hash_password("password123"),
        }

        upserted_user = await user.upsert(async_session, upsert_dict)

        assert upserted_user.id is not None
        assert upserted_user.username == "upsertuser"

    async def test_upsert_update(self, async_session: AsyncSession, user_factory):
        """Test upsert updates existing record."""
        user = user_factory(username="original")
        await user.save(async_session)

        upsert_dict = {"username": "updated"}
        upserted_user = await user.upsert(async_session, upsert_dict)

        assert upserted_user.id == user.id
        assert upserted_user.username == "updated"

    async def test_get_by_id(self, async_session: AsyncSession, user_factory):
        """Test retrieving by internal ID."""
        user = user_factory()
        await user.save(async_session)

        found_user = await User.get_by_id(async_session, user.id)

        assert found_user.id == user.id
        assert found_user.username == user.username

    async def test_get_by_id_not_found(self, async_session: AsyncSession):
        """Test get_by_id raises error when not found."""
        with pytest.raises(DatabaseError) as exc_info:
            await User.get_by_id(async_session, 999999)
        assert exc_info.value.status_code == 404

    async def test_get_by_uuid(self, async_session: AsyncSession, user_factory):
        """Test retrieving by UUID."""
        user = user_factory()
        await user.save(async_session)

        found_user = await User.get_by_uuid(async_session, user.uuid)

        assert found_user.uuid == user.uuid
        assert found_user.username == user.username

    async def test_get_by_uuid_not_found(self, async_session: AsyncSession):
        """Test get_by_uuid raises error when not found."""
        with pytest.raises(DatabaseError) as exc_info:
            await User.get_by_uuid(async_session, uuid.uuid4())
        assert exc_info.value.status_code == 404

    async def test_get_one(self, async_session: AsyncSession, user_factory):
        """Test get_one with filter kwargs."""
        user = user_factory(username="findme")
        await user.save(async_session)

        found_user = await User.get_one(async_session, username="findme")

        assert found_user.id == user.id
        assert found_user.username == "findme"

    async def test_get_one_not_found(self, async_session: AsyncSession):
        """Test get_one raises error when not found."""
        with pytest.raises(DatabaseError) as exc_info:
            await User.get_one(async_session, username="doesnotexist")
        assert exc_info.value.status_code == 404

    async def test_get_all(self, async_session: AsyncSession, user_factory):
        """Test get_all retrieves multiple records."""
        user1 = user_factory(username="user1")
        user2 = user_factory(username="user2")
        user3 = user_factory(username="user3")

        await user1.save(async_session)
        await user2.save(async_session)
        await user3.save(async_session)

        all_users = await User.get_all(async_session)

        assert len(all_users) >= 3
        usernames = [u.username for u in all_users]
        assert "user1" in usernames
        assert "user2" in usernames
        assert "user3" in usernames

    async def test_get_all_with_filter(self, async_session: AsyncSession, user_factory):
        """Test get_all with filter kwargs."""
        user1 = user_factory(username="specific_user")
        user2 = user_factory(username="other_user")

        await user1.save(async_session)
        await user2.save(async_session)

        users = await User.get_all(async_session, username="specific_user")

        assert len(users) == 1
        assert users[0].username == "specific_user"

    async def test_get_all_exclude_deleted(self, async_session: AsyncSession, user_factory):
        """Test get_all excludes soft-deleted records by default."""
        user1 = user_factory(username="active")
        user2 = user_factory(username="deleted")

        await user1.save(async_session)
        await user2.save(async_session)
        await user2.delete(async_session)

        users = await User.get_all(async_session)
        usernames = [u.username for u in users]

        assert "active" in usernames
        assert "deleted" not in usernames

    async def test_get_all_include_deleted(self, async_session: AsyncSession, user_factory):
        """Test get_all includes deleted records when requested."""
        user1 = user_factory(username="active")
        user2 = user_factory(username="deleted")

        await user1.save(async_session)
        await user2.save(async_session)
        await user2.delete(async_session)

        users = await User.get_all(async_session, include_deleted=True)
        usernames = [u.username for u in users]

        assert "active" in usernames
        assert "deleted" in usernames

    async def test_to_dict(self, async_session: AsyncSession, user_factory):
        """Test to_dict serialization."""
        user = user_factory(username="testuser")
        await user.save(async_session)

        user_dict = user.to_dict()

        assert isinstance(user_dict, dict)
        assert "uuid" in user_dict
        assert "username" in user_dict
        assert user_dict["username"] == "testuser"
        # Internal ID should not be included by default
        assert "id" not in user_dict

    async def test_to_dict_include_id(self, async_session: AsyncSession, user_factory):
        """Test to_dict with include_id option."""
        user = user_factory(username="testuser")
        await user.save(async_session)

        user_dict = user.to_dict(include_id=True)

        assert "id" in user_dict
        assert user_dict["id"] == user.id

    async def test_to_dict_datetime_serialization(self, async_session: AsyncSession, user_factory):
        """Test to_dict properly serializes datetime fields."""
        user = user_factory()
        await user.save(async_session)

        user_dict = user.to_dict()

        # created_at should be ISO format string
        assert isinstance(user_dict["created_at"], str)
        # Should be parseable as datetime
        datetime.fromisoformat(user_dict["created_at"])

    async def test_to_json(self, async_session: AsyncSession, user_factory):
        """Test to_json creates valid JSON string."""
        user = user_factory(username="jsonuser")
        await user.save(async_session)

        json_str = user.to_json()

        assert isinstance(json_str, str)
        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["username"] == "jsonuser"

    async def test_repr(self, async_session: AsyncSession, user_factory):
        """Test __repr__ method."""
        user = user_factory()
        await user.save(async_session)

        repr_str = repr(user)

        assert "User" in repr_str
        assert f"id={user.id}" in repr_str
        assert f"uuid={user.uuid}" in repr_str


@pytest.mark.asyncio
class TestBaseModelDecimalHandling:
    """Test Decimal handling in models."""

    async def test_decimal_to_dict_preserve_precision(self, async_session: AsyncSession, chain_factory, token_factory):
        """Test Decimal fields are preserved as strings by default."""
        chain = chain_factory()
        await chain.save(async_session)

        token = token_factory(chain.id, decimals=18)
        token.current_price_usd = Decimal("1234.567890123456789")
        await token.save(async_session)

        token_dict = token.to_dict(preserve_precision=True)

        # Should be string to preserve precision
        assert isinstance(token_dict["current_price_usd"], str)
        assert token_dict["current_price_usd"] == "1234.567890123456789"

    async def test_decimal_to_dict_as_float(self, async_session: AsyncSession, chain_factory, token_factory):
        """Test Decimal fields can be converted to float."""
        chain = chain_factory()
        await chain.save(async_session)

        token = token_factory(chain.id)
        token.current_price_usd = Decimal("1234.56")
        await token.save(async_session)

        token_dict = token.to_dict(preserve_precision=False)

        # Should be float
        assert isinstance(token_dict["current_price_usd"], float)
        assert abs(token_dict["current_price_usd"] - 1234.56) < 0.01


@pytest.mark.asyncio
class TestBaseModelDualID:
    """Test dual ID strategy (id and uuid)."""

    async def test_both_ids_generated(self, async_session: AsyncSession, user_factory):
        """Test both id and uuid are generated on save."""
        user = user_factory()
        await user.save(async_session)

        assert user.id is not None
        assert isinstance(user.id, int)
        assert user.uuid is not None
        assert isinstance(user.uuid, uuid.UUID)

    async def test_uuid_unique(self, async_session: AsyncSession, user_factory):
        """Test UUIDs are unique across instances."""
        user1 = user_factory()
        user2 = user_factory()

        await user1.save(async_session)
        await user2.save(async_session)

        assert user1.uuid != user2.uuid

    async def test_can_retrieve_by_either_id(self, async_session: AsyncSession, user_factory):
        """Test model can be retrieved by either id or uuid."""
        user = user_factory()
        await user.save(async_session)

        # Retrieve by integer id
        by_id = await User.get_by_id(async_session, user.id)
        assert by_id.username == user.username

        # Retrieve by UUID
        by_uuid = await User.get_by_uuid(async_session, user.uuid)
        assert by_uuid.username == user.username

        # Both should be the same record
        assert by_id.id == by_uuid.id
        assert by_id.uuid == by_uuid.uuid
