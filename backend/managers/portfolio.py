from backend.databases.models import Portfolio, Wallet
from backend.errors import DatabaseError
from backend.managers.base_crud import BaseCRUDManager
from backend.validators import get_uuid


class PortfolioManager(BaseCRUDManager[Portfolio]):
 
    @property
    def _model_class(self) -> type[Portfolio]:
        return Portfolio
    
    def add_wallet_to_portfolio(self, portfolio_id: str, wallet_id: str) -> None:
        portfolio = self.get(portfolio_id)
        wallet = Wallet.get(self.db, get_uuid(wallet_id))
        if wallet is None:
            raise DatabaseError(404, "Wallet is not found")
        if wallet in portfolio.wallets:
            raise DatabaseError(400, "Wallet is already in the portfolio")
        portfolio.wallets.append(wallet)
        self.db.commit()
    
    def remove_wallet_from_portfolio(self, portfolio_id: str, wallet_id: str) -> None:
        portfolio = self.get(portfolio_id)
        wallet = Wallet.get(self.db, get_uuid(wallet_id))
        if wallet is None:
            raise DatabaseError(404, "Wallet is not found")
        if wallet not in portfolio.wallets:
            raise DatabaseError(400, "Wallet is not in the portfolio")
        portfolio.wallets.remove(wallet)
        self.db.commit()
