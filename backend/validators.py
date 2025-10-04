import uuid


def get_uuid(value) -> uuid.UUID | None:
    """
    Get UUID from string or return None

    Returns:
        UUID or None
    """
    try:
        return value if isinstance(value, uuid.UUID) else uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return None


def get_uuid_or_rise(value) -> uuid.UUID:
    """
    Get UUID from string or rises an exception

    Returns:
        UUID

    Rises:
        :class:`ValueError` if value could not be converted to UUID
    """
    if value_uuid := get_uuid(value):
        return value_uuid
    raise ValueError()


def is_uuid(value: str) -> bool:
    return get_uuid(value) is not None
