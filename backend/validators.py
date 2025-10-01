import uuid


def get_uuid(value) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return None


def get_uuid_or_rise(value) -> uuid.UUID:
    return uuid.UUID(value)


def is_uuid(value: str) -> bool:
    return get_uuid(value) is not None
