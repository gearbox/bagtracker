import uuid


def get_uuid(value) -> uuid.UUID | None:
    """Returns UUID or None"""
    try:
        return value if isinstance(value, uuid.UUID) else uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return None


def get_uuid_or_rise(value) -> uuid.UUID:
    """Returns UUID or rises a ValueError"""
    if value_uuid := get_uuid(value):
        return value_uuid
    raise ValueError()


def is_uuid(value: str) -> bool:
    return get_uuid(value) is not None
