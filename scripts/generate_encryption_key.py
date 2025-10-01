"""
Generate a new encryption key for the application.

Usage:
    python scripts/generate_encryption_key.py
"""

from cryptography.fernet import Fernet


def main():
    key = Fernet.generate_key()
    print("\n" + "=" * 60)
    print("Generated Encryption Key:")
    print("=" * 60)
    print(f"\n{key.decode()}\n")
    print("=" * 60)
    print("\nAdd this to your .env file:")
    print(f'ENCRYPTION_KEY="{key.decode()}"')
    print("=" * 60)
    print("\n⚠️  SECURITY WARNING:")
    print("- Store this key securely")
    print("- Never commit this key to version control")
    print("- Use different keys for dev/staging/production")
    print("- Back up this key - data cannot be recovered without it!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
