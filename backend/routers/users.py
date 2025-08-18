from fastapi import APIRouter, Depends, Response
from fastapi import status as status_code

from backend import schemas
from backend.managers import UserManager

router = APIRouter()


@router.post("/user", response_model=schemas.User, status_code=status_code.HTTP_201_CREATED)
def create_user(
    user: schemas.UserCreate, 
    user_manager: UserManager = Depends(UserManager),
) -> schemas.User:
    return schemas.User.model_validate(user_manager.create_user(user).to_schema())

@router.get("/user/{user_id}", response_model=schemas.User)
def get_user_by_id(
    user_id: str, 
    user_manager: UserManager = Depends(UserManager),
) -> schemas.User:
    return schemas.User.model_validate(user_manager.get_user(user_id).to_schema())

@router.get("/users", response_model=schemas.UserAll)
def get_all_users(
    user_manager: UserManager = Depends(UserManager),
) -> schemas.UserAll:
    return schemas.UserAll.model_validate({"users": [user.to_schema() for user in user_manager.get_all_users()]})

@router.delete("/user/{user_id}", status_code=status_code.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    user_manager: UserManager = Depends(UserManager),
) -> Response:
    user_manager.delete_user(user_id)
    return Response(status_code=status_code.HTTP_204_NO_CONTENT)
