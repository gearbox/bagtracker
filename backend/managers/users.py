from backend import schemas
from backend.databases.models import User
from backend.errors import UserError
from backend.managers.base_crud import BaseCRUDManager
from backend.validators import get_uuid


class UserManager(BaseCRUDManager):
    @property
    def _model_class(self) -> type[User]:
        return User

    def create_user(self, user: schemas.UserCreateOrUpdate) -> User:
        # TODO: check if we can remove the username presence from router and replace it with validator in schema
        if not user.username:
            raise UserError(status_code=400, exception_message="Username field is required")
        new_user = User(**user.model_dump())
        existing_user = self.db.query(User).filter(User.username == new_user.username).first()
        if existing_user:
            raise UserError(status_code=400, exception_message="This username is already taken")
        self._save_or_raise(new_user)
        return new_user

    def get_user(self, username_or_id: str) -> User:
        existing_user = None
        if user_id := get_uuid(username_or_id):
            existing_user = User.get(self.db, user_id)
        else:
            existing_user = User.get_one_by_kwargs(self.db, username=username_or_id)
        if not existing_user:
            raise UserError(status_code=404, exception_message="User not found")
        return existing_user

    def get_user_by_email(self, email: str) -> User:
        user = User.get_one_by_kwargs(self.db, email=email)
        if not user:
            raise UserError(status_code=404, exception_message="User not found")
        return user

    def update_user(self, username_or_id: str, user: schemas.UserCreateOrUpdate) -> User:
        if not user.username:
            raise UserError(status_code=400, exception_message="Username field is required")
        return self.get_user(username_or_id).update(self.db, update_dict=user.model_dump())

    def patch_user(self, username_or_id: str, user: schemas.UserCreateOrUpdate) -> User:
        return self.get_user(username_or_id).update(self.db, update_dict=user.model_dump(exclude_unset=True))
