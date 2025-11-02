import traceback

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic_core import ValidationError


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

    def __init__(self, status_code: int | None = None, exception_message: str | None = None):
        if status_code:
            self.status_code = status_code
        if exception_message:
            self.message = exception_message


class BadRequestException(GeneralProcessingException):
    """Bad request exception class"""

    message = "Bad request problem has occurred"
    status_code = 400

    def __init__(self, exception_message=None):
        super().__init__(exception_message=exception_message)


class UnexpectedException(GeneralProcessingException):
    """Unexpected exception class"""

    message = "Unexpected problem has occurred"
    status_code = 500

    def __init__(self, exception_message=None):
        super().__init__(status_code=500, exception_message=exception_message)


class NotAuthorizedException(GeneralProcessingException):
    """Authorization exception class"""

    message = "Invalid authorization problem"
    status_code = 403

    def __init__(self, exception_message=None):
        if exception_message:
            self.message = f"Failed to pass authorization. {exception_message}"


class DatabaseError(GeneralProcessingException):
    """Database-related exception class"""

    message = "Database-related problem has occurred"
    status_code = 500

    def __init__(self, status_code: int | None = None, exception_message: str | None = None):
        super().__init__(status_code=status_code, exception_message=exception_message)


class UserError(GeneralProcessingException):
    """User-related exception class"""

    message = "User not found"
    status_code = 404

    def __init__(self, status_code: int | None = None, exception_message: str | None = None):
        super().__init__(status_code=status_code, exception_message=exception_message)


class WalletError(GeneralProcessingException):
    """Wallet-related exception class"""

    message = "Wallet not found"
    status_code = 404

    def __init__(self, status_code: int | None = None, exception_message: str | None = None):
        super().__init__(status_code=status_code, exception_message=exception_message)


class TransactionError(GeneralProcessingException):
    """Transaction-related exception class"""

    message = "Transaction cannot be processed"
    status_code = 400

    def __init__(self, status_code: int | None = None, exception_message: str | None = None):
        super().__init__(status_code=status_code, exception_message=exception_message)
