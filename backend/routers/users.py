from fastapi import APIRouter, Depends, Response
from fastapi import status as status_code
from sqlalchemy.orm import Session

from backend import schemas
from backend.managers import UserManager

router = APIRouter()


@router.post("/user", response_model=schemas.User, status_code=status_code.CREATED)
def create_user(
    user: schemas.UserCreate, 
    user_manager: UserManager = Depends(UserManager),
) -> schemas.User:
    return schemas.User.model_validate(user_manager.create_user(user).to_schema())

@router.get("/user/{user_id}", response_model=schemas.User)
def get_user_by_id(
    user_id: int, 
    user_manager: UserManager = Depends(UserManager),
) -> schemas.User:
    return schemas.User.model_validate(user_manager.get_user(user_id).to_schema())

@router.delete("/user/{user_id}", status_code=status_code.NO_CONTENT)
def delete_user(
    user_id: int,
    user_manager: UserManager = Depends(UserManager),
) -> Response:
    user_manager.delete_user(user_id)
    return Response(status_code=status_code.NO_CONTENT)
