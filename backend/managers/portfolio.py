import uuid

from backend.databases.models import Portfolio, Wallet
from backend.errors import DatabaseError
from backend.managers.base_crud import BaseCRUDManager


class PortfolioManager(BaseCRUDManager[Portfolio]):
    eager_load = [
        "owner",
        "wallets",
        "wallets.chain",
        "cex_accounts",
    ]

    @property
    def _model_class(self) -> type[Portfolio]:
        return Portfolio

    async def add_wallet_to_portfolio(self, portfolio_uuid: str, wallet_uuid: str) -> None:
        portfolio = await self.get(portfolio_uuid)
        wallet = await Wallet.get_by_uuid(self.db, uuid.UUID(wallet_uuid))
        if wallet in portfolio.wallets:
            raise DatabaseError(400, "Wallet is already in the portfolio")
        wallet.portfolio_id = portfolio.id
        await self.db.commit()

    async def remove_wallet_from_portfolio(self, portfolio_uuid: str, wallet_uuid: str) -> None:
        portfolio = await self.get(portfolio_uuid)
        wallet = await Wallet.get_by_uuid(self.db, uuid.UUID(wallet_uuid))
        if wallet not in portfolio.wallets:
            raise DatabaseError(400, "Wallet is not in the portfolio")
        wallet.portfolio_id = None
        await self.db.commit()

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
