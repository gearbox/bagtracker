def get_erc20_token_list() -> list[dict]:
    ERC20_TOKENS = [
        {"symbol": "STETH", "address": "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84", "decimals": 18},
        {"symbol": "WETH", "address": "0xC02aaA39b223FE8D0A0e5C4F3C8B8B8B8B8B8B8B", "decimals": 18},
        {"symbol": "WBTC", "address": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599", "decimals": 8},
        {"symbol": "USDT", "address": "0xdAC17F958D2ee523a2206206994597C13D831ec7", "decimals": 6},
        {"symbol": "USDC", "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "decimals": 6},
        {"symbol": "DAI", "address": "0x6B175474E89094C44Da98b954EedeAC495271d0F", "decimals": 18},
    ]
    return ERC20_TOKENS
