from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi import status as status_code

from backend import schemas
from backend.dependencies import token_auth
from backend.managers import UserManager

router = APIRouter()


@router.post("/sign-up", response_model=schemas.User, status_code=status_code.HTTP_201_CREATED)
async def sign_up_user(
    user: schemas.UserSignUp,
    user_manager: Annotated[UserManager, Depends(UserManager)],
) -> schemas.User:
    return schemas.User.model_validate(await user_manager.sign_up(user))


@router.get("/user/{username}", response_model=schemas.User)
async def get_user(username: str, user_manager: Annotated[UserManager, Depends(UserManager)]) -> schemas.User:
    user_obj = await user_manager.get_user(username)
    return schemas.User.model_validate(user_obj.to_schema())


@router.put("/user/{username}", response_model=schemas.User)
async def update_user(
    username: str, user: schemas.UserCreateOrUpdate, user_manager: Annotated[UserManager, Depends(UserManager)]
) -> schemas.User:
    user_obj = await user_manager.update_user(username, user)
    return schemas.User.model_validate(user_obj.to_schema())


@router.patch("/user/{username}", response_model=schemas.User)
async def patch_user(
    username: str, user: schemas.UserCreateOrUpdate, user_manager: Annotated[UserManager, Depends(UserManager)]
) -> schemas.User:
    user_obj = await user_manager.patch_user(username, user)
    return schemas.User.model_validate(user_obj.to_schema())


@router.delete("/user/{username}", status_code=status_code.HTTP_204_NO_CONTENT)
async def delete_user(username: str, user_manager: Annotated[UserManager, Depends(UserManager)]) -> Response:
    user = await user_manager.get_user(username)
    await user_manager.delete(user.id)
    return Response(status_code=status_code.HTTP_204_NO_CONTENT)


# User Management
#################


@router.post(
    "/user-management/user",
    tags=["User Management"],
    response_model=schemas.User,
    status_code=status_code.HTTP_201_CREATED,
)
async def create_user(
    user: schemas.UserCreateOrUpdate,
    user_manager: Annotated[UserManager, Depends(UserManager)],
) -> schemas.User:
    user_obj = await user_manager.create_user(user)
    return schemas.User.model_validate(user_obj.to_schema())


@router.get(
    "/user-management/users",
    tags=["User Management"],
    dependencies=token_auth,
    response_model=schemas.UserMgmtAll,
)
async def get_all_users(
    user_manager: Annotated[UserManager, Depends(UserManager)],
) -> schemas.UserMgmtAll:
    users = await user_manager.get_all(include_deleted=True)
    return schemas.UserMgmtAll.model_validate({"users": users})


@router.delete(
    "/user-management/user/{user_uuid}",
    tags=["User Management"],
    dependencies=token_auth,
    status_code=status_code.HTTP_204_NO_CONTENT,
)
async def delete_user_by_id(
    user_uuid: str,
    user_manager: Annotated[UserManager, Depends(UserManager)],
) -> Response:
    await user_manager.delete(user_uuid)
    return Response(status_code=status_code.HTTP_204_NO_CONTENT)
