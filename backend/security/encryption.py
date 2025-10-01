from cryptography.fernet import Fernet, InvalidToken
from loguru import logger
from sqlalchemy import String, TypeDecorator
from sqlalchemy.engine import Dialect

from backend.settings import settings


class EncryptionManager:
    """
    Manages encryption keys for the application.
    """

    _primary_key: bytes | None = None
    _secondary_key: bytes | None = None  # For key rotation

    @classmethod
    def initialize(cls, primary_key: str | None = None, secondary_key: str | None = None):
        """
        Initialize encryption keys.

        Args:
            primary_key: Base64-encoded Fernet key (32 bytes)
            secondary_key: Optional old key for rotation
        """
        # Get from environment if not provided
        primary_key = primary_key or settings.encryption_key
        secondary_key = secondary_key or settings.encryption_key_old

        if not primary_key:
            raise ValueError(
                "ENCRYPTION_KEY not set. Generate one with: "
                "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )

        cls._primary_key = primary_key.encode() if isinstance(primary_key, str) else primary_key
        cls._secondary_key = secondary_key.encode() if isinstance(secondary_key, str) else secondary_key

    @classmethod
    def get_primary_cipher(cls) -> Fernet:
        """Get Fernet cipher with primary key"""
        if not cls._primary_key:
            raise RuntimeError("Encryption not initialized. Call EncryptionManager.initialize() first.")
        return Fernet(cls._primary_key)

    @classmethod
    def get_secondary_cipher(cls) -> Fernet | None:
        """Get Fernet cipher with secondary key (for rotation)"""
        return Fernet(cls._secondary_key) if cls._secondary_key else None

    @classmethod
    def encrypt(cls, value: str) -> bytes:
        """Encrypt a string value"""
        if not value:
            return b""
        cipher = cls.get_primary_cipher()
        return cipher.encrypt(value.encode())

    @classmethod
    def decrypt(cls, encrypted_value: bytes) -> str:
        """
        Decrypt a value, attempting secondary key if primary fails.
        This supports key rotation.
        """
        if not encrypted_value:
            return ""

        # Try primary key first
        try:
            cipher = cls.get_primary_cipher()
            return cipher.decrypt(encrypted_value).decode()
        except InvalidToken as e:
            if secondary_cipher := cls.get_secondary_cipher():
                try:
                    return secondary_cipher.decrypt(encrypted_value).decode()
                except InvalidToken as exc:
                    raise ValueError("Failed to decrypt with both primary and secondary keys") from exc
            raise ValueError("Failed to decrypt value") from e

    @classmethod
    def generate_key(cls) -> str:
        """Generate a new Fernet key"""
        return Fernet.generate_key().decode()

    @classmethod
    def rotate_key(cls, session, model_class, encrypted_columns: list[str]) -> None:
        """
        Rotate encryption keys for a model.

        Usage:
            EncryptionManager.rotate_key(
                session,
                CexAccount,
                ['api_key', 'api_secret', 'passphrase']
            )
        """
        if not cls._secondary_key:
            raise ValueError("Secondary key not set. Cannot rotate.")

        records = session.query(model_class).all()

        for record in records:
            for column in encrypted_columns:
                if encrypted_value := getattr(record, column):
                    # Decrypt with old key, encrypt with new key
                    decrypted = cls.decrypt(encrypted_value)
                    setattr(record, column, decrypted)  # TypeDecorator will re-encrypt

        session.commit()
        print(f"✅ Rotated keys for {len(records)} {model_class.__name__} records")


class EncryptedString(TypeDecorator):
    """
    SQLAlchemy type decorator for automatic encryption/decryption.

    Usage:
        api_key: Mapped[str | None] = mapped_column(EncryptedString(500), nullable=True)

    Features:
    - Automatic encryption on write
    - Automatic decryption on read
    - Transparent to application code
    - Supports NULL values
    """

    impl = String
    cache_ok = True

    def __init__(self, length: int = 500, *args, **kwargs):
        """
        Args:
            length: Database column length (encrypted data is longer than plain text)
                   Rule of thumb: (plaintext_length * 1.5) + 100
        """
        super().__init__(length, *args, **kwargs)

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        """Called when saving to database - encrypts the value"""
        if value is None:
            return None

        if not value:  # Empty string
            return ""

        encrypted_bytes = EncryptionManager.encrypt(value)
        # Store as base64 string for database compatibility
        return encrypted_bytes.decode("utf-8")

    def process_result_value(self, value: str | None, dialect: Dialect) -> str | None:
        """Called when reading from database - decrypts the value"""
        if value is None or value == "":
            return value

        # Convert back to bytes and decrypt
        encrypted_bytes = value.encode("utf-8")
        return EncryptionManager.decrypt(encrypted_bytes)


def init_encryption(primary_key: str | None = None, secondary_key: str | None = None):
    EncryptionManager.initialize(
        primary_key=primary_key or settings.encryption_key, secondary_key=secondary_key or settings.encryption_key_old
    )
    logger.info("✅ Encryption initialized")
