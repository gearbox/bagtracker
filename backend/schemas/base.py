from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_serializer


class APIBaseModel(BaseModel):
    """Base model for all API responses with proper Decimal handling"""

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            Decimal: str,
            datetime: lambda v: v.isoformat() if v else None,
            UUID: str,
        },
    )

    @field_serializer("*")
    def serialize_all_fields(self, value: Any, _info) -> Any:
        """Global serializer for all fields"""
        if isinstance(value, Decimal):
            return str(value)
        elif isinstance(value, datetime):
            return value.isoformat() if value else None
        elif isinstance(value, UUID):
            return str(value)
        return value
