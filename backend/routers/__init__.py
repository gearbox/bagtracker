from fastapi import APIRouter

from backend.dependencies import common, token_auth
from backend.routers import (
    healthcheck, 
    info, 
    eth, 
    users, 
    wallets, 
    transactions, 
    portfolio, 
    chains,
    tokens,
    auth
)

main_router = APIRouter(dependencies=common)
main_router.include_router(healthcheck.router, tags=['Health check'])
main_router.include_router(info.router, tags=['Info'], dependencies=token_auth)
main_router.include_router(eth.router, tags=['Ethereum'])
main_router.include_router(auth.router, tags=['Auth'])
main_router.include_router(users.router, tags=['Users'])
main_router.include_router(wallets.router, tags=['Wallets'])
main_router.include_router(transactions.router, tags=['Transactions'])
main_router.include_router(portfolio.router, tags=['Portfolio'])
main_router.include_router(chains.router, tags=['Chains'])
main_router.include_router(tokens.router, tags=['Tokens'])
