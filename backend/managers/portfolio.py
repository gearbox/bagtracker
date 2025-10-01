import uuid

from backend.databases.models import Portfolio, Wallet
from backend.errors import DatabaseError
from backend.managers.base_crud import BaseCRUDManager


class PortfolioManager(BaseCRUDManager[Portfolio]):
    @property
    def _model_class(self) -> type[Portfolio]:
        return Portfolio

    def add_wallet_to_portfolio(self, portfolio_uuid: str, wallet_uuid: str) -> None:
        portfolio = self.get(portfolio_uuid)
        wallet = Wallet.get_by_uuid(self.db, uuid.UUID(wallet_uuid))
        if wallet is None:
            raise DatabaseError(404, "Wallet is not found")
        if wallet in portfolio.wallets:
            raise DatabaseError(400, "Wallet is already in the portfolio")
        portfolio.wallets.append(wallet)
        self.db.commit()

    def remove_wallet_from_portfolio(self, portfolio_uuid: str, wallet_uuid: str) -> None:
        portfolio = self.get(portfolio_uuid)
        wallet = Wallet.get_by_uuid(self.db, uuid.UUID(wallet_uuid))
        if wallet is None:
            raise DatabaseError(404, "Wallet is not found")
        if wallet not in portfolio.wallets:
            raise DatabaseError(400, "Wallet is not in the portfolio")
        portfolio.wallets.remove(wallet)
        self.db.commit()

    # def get_portfolio_summary(self, user_id: str) -> dict[str, Any]:
    #     """Get portfolio summary with proper decimal aggregation"""
    #     from sqlalchemy import func

    #     # Use database aggregation to maintain precision
    #     result = session.query(
    #         func.sum(Balance.value_usd).label('total_value'),
    #         func.count(Balance.id).label('token_count'),
    #         func.avg(Balance.value_usd).label('avg_value')
    #     ).filter(
    #         Balance.wallet_id.in_(
    #             session.query(Wallet.id).filter(Wallet.user_id == user_id)
    #         )
    #     ).first()

    #     return {
    #         'total_value_usd': str(result.total_value or Decimal('0')),
    #         'token_count': result.token_count or 0,
    #         'avg_value_usd': str(result.avg_value or Decimal('0')),
    #     }
