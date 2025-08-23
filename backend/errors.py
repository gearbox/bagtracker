import traceback

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic_core import ValidationError
from loguru import logger


async def handle_exception(request: Request, exc: Exception) -> JSONResponse:
    code = 500
    message = str(exc.args)
    logger.error(traceback.format_exc())
    if isinstance(exc, GeneralProcessingException):
        code = exc.status_code
        message = exc.message
    elif isinstance(exc, ValidationError):
        errors_kwargs = {"include_url": False}
        return JSONResponse(
            status_code=code,
            content=jsonable_encoder({"detail": exc.errors(**errors_kwargs)}),
        )
    return JSONResponse(
        status_code=code,
        content={"type": str(type(exc)), "message": message},
    )


class GeneralProcessingException(Exception):
    """basic exception class"""

    message = "Unknown backend problem have happened"
    status_code = 500

    def __init__(self, response_text=None):
        if response_text:
            self.message = f"{response_text}"


class NotAuthorizedException(GeneralProcessingException):
    """Authorisation exception class"""

    message = "Invalid authorization problem"
    status_code = 403

    def __init__(self, response_text=None):
        if response_text:
            self.message = f"Failed to pass authorization. {response_text}"


class DatabaseError(GeneralProcessingException):
    """Database-related exception class"""

    status_code = 500
    message = "Database-related problem has occurred"

    def __init__(self, status_code: int | None = None, exception_message: str | None = None):
        if status_code:
            self.status_code = status_code
        if exception_message:
            self.message = exception_message

class UserError(GeneralProcessingException):
    """User-related exception class"""

    status_code = 404
    message = "User not found"

    def __init__(self, status_code: int | None = None, exception_message: str | None = None):
        if status_code:
            self.status_code = status_code
        if exception_message:
            self.message = exception_message


class WalletError(GeneralProcessingException):
    """Wallet-related exception class"""

    status_code = 400
    message = "Wallet not found"

    def __init__(self, status_code: int | None = None, exception_message: str | None = None):
        if status_code:
            self.status_code = status_code
        if exception_message:
            self.message = exception_message
