from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi import status as status_code

from backend import schemas
from backend.managers import AuthManager

router = APIRouter()


@router.post("/login", response_model=schemas.LoginResponse, status_code=status_code.HTTP_200_OK)
async def login(
    login_data: schemas.LoginRequest,
    auth_manager: Annotated[AuthManager, Depends(AuthManager)],
) -> schemas.LoginResponse:
    return schemas.LoginResponse.model_validate(await auth_manager.login(login_data))
