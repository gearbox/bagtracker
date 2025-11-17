"""
Telegram Mini App authentication utilities.

This module provides utilities for verifying Telegram Mini App authentication data.
See: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

import hashlib
import hmac
from typing import Any

from backend.settings import settings


def verify_telegram_auth(auth_data: dict[str, Any], bot_token: str | None = None) -> bool:
    """
    Verify Telegram Mini App authentication data.

    Args:
        auth_data: Dictionary containing Telegram auth data (id, first_name, etc.)
        bot_token: Telegram bot token (if None, uses TELEGRAM_BOT_TOKEN from settings)

    Returns:
        True if authentication data is valid, False otherwise

    Example:
        >>> auth_data = {
        ...     "id": 123456789,
        ...     "first_name": "John",
        ...     "username": "johndoe",
        ...     "auth_date": 1234567890,
        ...     "hash": "abc123..."
        ... }
        >>> verify_telegram_auth(auth_data)
        True
    """
    if bot_token is None:
        bot_token = getattr(settings, "telegram_bot_token", None)
        if not bot_token:
            # If no bot token configured, skip verification (dev mode)
            # WARNING: This is insecure! Always set TELEGRAM_BOT_TOKEN in production
            return True

    # Extract hash from auth_data
    received_hash = auth_data.get("hash")
    if not received_hash:
        return False

    # Create data check string
    data_check_arr = [f"{key}={value}" for key, value in sorted(auth_data.items()) if key != "hash"]
    data_check_string = "\n".join(data_check_arr)

    # Create secret key
    secret_key = hashlib.sha256(bot_token.encode()).digest()

    # Calculate hash
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    # Compare hashes
    return hmac.compare_digest(calculated_hash, received_hash)


def verify_telegram_auth_data(
    telegram_id: int,
    first_name: str | None,
    last_name: str | None,
    username: str | None,
    photo_url: str | None,
    auth_date: int,
    hash_value: str,
    bot_token: str | None = None,
) -> bool:
    """
    Verify Telegram authentication data from individual parameters.

    Args:
        telegram_id: Telegram user ID
        first_name: User's first name
        last_name: User's last name
        username: Telegram username
        photo_url: Profile photo URL
        auth_date: Authentication timestamp
        hash_value: Authentication hash
        bot_token: Telegram bot token (if None, uses TELEGRAM_BOT_TOKEN from settings)

    Returns:
        True if authentication data is valid, False otherwise
    """
    auth_data = {"id": telegram_id, "auth_date": auth_date, "hash": hash_value}

    if first_name:
        auth_data["first_name"] = first_name
    if last_name:
        auth_data["last_name"] = last_name
    if username:
        auth_data["username"] = username
    if photo_url:
        auth_data["photo_url"] = photo_url

    return verify_telegram_auth(auth_data, bot_token)
