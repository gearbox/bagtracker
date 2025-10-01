"""
Rotate encryption keys for all encrypted fields.

Usage:
    # Set both keys in environment
    export ENCRYPTION_KEY="new_key_here"
    export ENCRYPTION_KEY_OLD="old_key_here"

    # Run rotation
    python scripts/rotate_encryption_keys.py
"""

import sys

from backend.databases.factory import get_db_session
from backend.databases.models.portfolio import CexAccount
from backend.security.encryption import EncryptionManager
from backend.settings import settings


def _rotate_keys_for_cex_account(db):
    """Rotate keys for CexAccount"""
    EncryptionManager.rotate_key(db, CexAccount, ["api_key", "api_secret", "passphrase"])

    print("✅ Key rotation completed successfully!")
    print("📝 Next steps:")
    print("1. Remove ENCRYPTION_KEY_OLD from environment")
    print("2. Update your secrets management system")
    print("3. Test API connections to verify decryption works")


def main():
    if not settings.encryption_key_old:
        print("❌ Error: ENCRYPTION_KEY_OLD not set")
        print("Set it to your current key before rotation")
        sys.exit(1)

    print("🔄 Starting encryption key rotation...")
    print(f"📊 Old key: {settings.encryption_key_old:10]}...")
    print(f"📊 New key: {settings.encryption_key:10]}...")

    # Initialize with both keys
    EncryptionManager.initialize(primary_key=settings.encryption_key, secondary_key=settings.encryption_key_old)

    # Get database session
    db = next(get_db_session())

    try:
        _rotate_keys_for_cex_account(db)
    except Exception as e:
        print(f"❌ Error during rotation: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
