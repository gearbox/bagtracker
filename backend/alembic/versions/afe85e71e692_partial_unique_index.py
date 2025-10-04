"""Partial Unique Index

Revision ID: afe85e71e692
Revises: 6a25ca2a49ad
Create Date: 2025-10-04 03:09:29.745910

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "afe85e71e692"
down_revision: str | Sequence[str] | None = "6a25ca2a49ad"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop existing unique constraints
    op.drop_index("ix_users_username", table_name="users")
    op.drop_constraint("users_email_key", "users", type_="unique")

    # Add partial unique indexes (only for non-deleted records)
    op.execute("""
        CREATE UNIQUE INDEX ix_users_username_active 
        ON users (username) 
        WHERE is_deleted = false
    """)

    op.execute("""
        CREATE UNIQUE INDEX ix_users_email_active 
        ON users (email) 
        WHERE is_deleted = false
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_users_username_active", table_name="users")
    op.drop_index("ix_users_email_active", table_name="users")

    # Restore original constraints
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_unique_constraint("users_email_key", "users", ["email"])
