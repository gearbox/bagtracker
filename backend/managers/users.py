from backend import schemas
from backend.databases.models import User
from backend.errors import UserError
from backend.managers.base_crud import BaseCRUDManager
from backend.security import hash_password
from backend.validators import get_uuid


class UserManager(BaseCRUDManager):
    @property
    def _model_class(self) -> type[User]:
        return User

    def sign_up(self, user_data: schemas.UserSignUp) -> User:
        """Register a new user with hashed password"""
        # Check if username already exists
        if self.db.query(User).filter(User.username == user_data.username).first():
            raise UserError(status_code=400, exception_message="This username is already taken")

        # Check if email already exists
        if user_data.email and self.db.query(User).filter(User.email == user_data.email).first():
            raise UserError(status_code=400, exception_message="This email is already registered")

        # Create user with hashed password
        user_dict = user_data.model_dump(exclude={"password"})
        user_dict["password_hash"] = hash_password(user_data.password)

        new_user = User(**user_dict)
        new_user.save(self.db)
        return new_user

    def create_user(self, user: schemas.UserCreateOrUpdate) -> User:
        new_user = User(**user.model_dump())
        if self.db.query(User).filter(User.username == new_user.username).first():
            raise UserError(status_code=400, exception_message="This username is already taken")
        new_user.save(self.db)
        return new_user

    def get_user(self, username_or_id: str) -> User:
        existing_user = None
        if user_id := get_uuid(username_or_id):
            existing_user = self.model.get(self.db, user_id)
        else:
            existing_user = User.get_one(self.db, username=username_or_id)
        if not existing_user:
            raise UserError(status_code=404, exception_message="User not found")
        return existing_user

    def get_user_by_email(self, email: str) -> User:
        if user := User.get_one(self.db, email=email):
            return user
        raise UserError(status_code=404, exception_message="User not found")

    def update_user(self, username_or_id: str, user: schemas.UserCreateOrUpdate) -> User:
        if not user.username:
            raise UserError(status_code=400, exception_message="Username field is required")
        return self.get_user(username_or_id).update(self.db, update_dict=user.model_dump())

    def patch_user(self, username_or_id: str, user: schemas.UserCreateOrUpdate) -> User:
        return self.get_user(username_or_id).update(self.db, update_dict=user.model_dump(exclude_unset=True))
