from typing import TYPE_CHECKING

from fastapi import Depends
import sqlalchemy.exc

from backend.databases.postgres import get_db_session
from backend.databases.models import Wallet, User
from backend import schemas
from backend.errors import DatabaseError, UserError, WalletError
from backend.validators import is_uuid, get_uuid

if TYPE_CHECKING:
    from sqlalchemy.orm import Session as DBSession


class WalletManager:
    def __init__(self, db: "DBSession" = Depends(get_db_session)) -> None:
        self.db = db

    def _if_user_exists(self, username_or_id: str) -> User:
        if user_id := get_uuid(username_or_id):
            user = User.get(self.db, user_id)
        else:
            user = User.get_by_kwargs(self.db, username=username_or_id)
        if not user:
            raise UserError(status_code=404, exception_message="User not found")
        return user

    def create_wallet(self, wallet: schemas.WalletCreate, username_or_id: str) -> Wallet:
        user = self._if_user_exists(username_or_id)
        new_wallet = Wallet(**wallet.model_dump(), user_id=user.id)
        self._wallet_save_or_raise(new_wallet)
        return new_wallet

    def _wallet_save_or_raise(self, wallet: Wallet) -> None:
        try:
            wallet.save(self.db)
        except sqlalchemy.exc.IntegrityError as e:
            if "duplicate key value" in str(e):
                pass
            else:
                raise DatabaseError(status_code=500, exception_message=f"Database integrity error: {str(e)}") from e
        except sqlalchemy.exc.SQLAlchemyError as e:
            raise DatabaseError(status_code=500, exception_message=f"Internal database error: {str(e)}") from e
        except Exception as e:
            raise DatabaseError(status_code=500, exception_message=f"Internal server error: {str(e)}") from e

    def get_wallets_by_user(self, username_or_id: str) -> list[Wallet]:
        if is_uuid(username_or_id):
            return Wallet.get_many_by_kwargs(self.db, user_id=username_or_id)
        else:
            user = User.get_by_kwargs(self.db, username=username_or_id)
            return user.wallets if user else []

    def get_wallet(self, wallet_id: str) -> Wallet:
        if _id := get_uuid(wallet_id):
            if wallet := Wallet.get(self.db, _id):
                return wallet
        raise WalletError(status_code=404, exception_message="Wallet not found")

    def update_wallet(self, wallet_id: str, wallet_data: schemas.WalletCreate) -> Wallet:
        wallet = self.get_wallet(wallet_id)
        wallet.update(self.db, update_dict=wallet_data.model_dump())
        return wallet

    def delete_wallet(self, wallet_id: str) -> None:
        wallet = self.get_wallet(wallet_id)
        try:
            wallet.delete(self.db)
        except sqlalchemy.exc.SQLAlchemyError as e:
            raise DatabaseError(status_code=500, exception_message=f"Internal database error: {str(e)}") from e
        except Exception as e:
            raise DatabaseError(status_code=500, exception_message=f"Internal server error: {str(e)}") from e
