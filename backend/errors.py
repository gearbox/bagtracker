import traceback

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from loguru import logger


async def handle_exception(request: Request, exc: Exception):
    code = 500
    message = exc.message if hasattr(exc, "message") else str(exc.args)
    logger.error(traceback.format_exc())
    if isinstance(exc, GeneralProcessingException):
        code = exc.status_code
    elif hasattr(exc, "errors"):
        return JSONResponse(
            status_code=code,
            content=jsonable_encoder({"detail": exc.errors(include_url=False)}),
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
