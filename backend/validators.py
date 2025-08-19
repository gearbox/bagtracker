import uuid

def get_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except ValueError:
        return None

def is_uuid(value: str) -> bool:
    return get_uuid(value) is not None
