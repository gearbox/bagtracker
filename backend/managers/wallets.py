from backend.databases.models import Wallet
from backend.managers.base_crud import BaseCRUDManager


class WalletManager(BaseCRUDManager[Wallet]):
    # Define relationships to eager load
    eager_load = [
        "chain",  # Load the chain relationship
        "transactions",  # Load all transactions
        "balances",  # Load current balances
        "portfolio",  # Load portfolio if exists
    ]

    @property
    def _model_class(self) -> type[Wallet]:
        return Wallet

    async def get_by_address(self, address: str) -> Wallet:
        return await self.get_one(address=address)
