from sqlalchemy import text

from backend.seeds.seed import SeederBase

TOKENS = [
    # Ethereum mainnet tokens (chain_id: 1)
    {
        "id": 1,
        "chain_id": 1,
        "symbol": "ETH",
        "name": "Ethereum",
        "decimals": 18,
        "contract_address": None,
        "contract_address_lowercase": None,
        "token_standard": "native",
        "is_native": True,
        "coingecko_id": "ethereum",
        "coinmarketcap_id": 1027,
    },
    {
        "id": 2,
        "chain_id": 1,
        "symbol": "USDC",
        "name": "USD Coin",
        "decimals": 6,
        "contract_address": "0xA0b86a33E6441D0C41c62A4d9DCD3CA1B6c8B2F9",
        "contract_address_lowercase": "0xa0b86a33e6441d0c41c62a4d9dcd3ca1b6c8b2f9",
        "token_standard": "ERC-20",
        "is_native": False,
        "coingecko_id": "usd-coin",
        "coinmarketcap_id": 3408,
    },
    {
        "id": 3,
        "chain_id": 1,
        "symbol": "USDT",
        "name": "Tether USD",
        "decimals": 6,
        "contract_address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "contract_address_lowercase": "0xdac17f958d2ee523a2206206994597c13d831ec7",
        "token_standard": "ERC-20",
        "is_native": False,
        "coingecko_id": "tether",
        "coinmarketcap_id": 825,
    },
    {
        "id": 4,
        "chain_id": 1,
        "symbol": "WETH",
        "name": "Wrapped Ether",
        "decimals": 18,
        "contract_address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "contract_address_lowercase": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        "token_standard": "ERC-20",
        "is_native": False,
        "coingecko_id": "weth",
        "coinmarketcap_id": 2396,
    },
    # Polygon tokens (chain_id: 2)
    {
        "id": 10,
        "chain_id": 2,
        "symbol": "MATIC",
        "name": "Polygon",
        "decimals": 18,
        "contract_address": None,
        "contract_address_lowercase": None,
        "token_standard": "native",
        "is_native": True,
        "coingecko_id": "matic-network",
        "coinmarketcap_id": 3890,
    },
    {
        "id": 11,
        "chain_id": 2,
        "symbol": "USDC",
        "name": "USD Coin",
        "decimals": 6,
        "contract_address": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
        "contract_address_lowercase": "0x2791bca1f2de4661ed88a30c99a7a9449aa84174",
        "token_standard": "ERC-20",
        "is_native": False,
        "coingecko_id": "usd-coin-polygon-pos",
        "coinmarketcap_id": 3408,
    },
    # BSC tokens (chain_id: 3)
    {
        "id": 20,
        "chain_id": 3,
        "symbol": "BNB",
        "name": "BNB",
        "decimals": 18,
        "contract_address": None,
        "contract_address_lowercase": None,
        "token_standard": "native",
        "is_native": True,
        "coingecko_id": "binancecoin",
        "coinmarketcap_id": 1839,
    },
    {
        "id": 21,
        "chain_id": 3,
        "symbol": "USDT",
        "name": "Tether USD",
        "decimals": 18,
        "contract_address": "0x55d398326f99059fF775485246999027B3197955",
        "contract_address_lowercase": "0x55d398326f99059ff775485246999027b3197955",
        "token_standard": "BEP-20",
        "is_native": False,
        "coingecko_id": "tether-bsc",
        "coinmarketcap_id": 825,
    },
    # Tron tokens (chain_id: 100)
    {
        "id": 100,
        "chain_id": 100,
        "symbol": "TRX",
        "name": "TRON",
        "decimals": 6,
        "contract_address": None,
        "contract_address_lowercase": None,
        "token_standard": "native",
        "is_native": True,
        "coingecko_id": "tron",
        "coinmarketcap_id": 1958,
    },
    {
        "id": 101,
        "chain_id": 100,
        "symbol": "USDT",
        "name": "Tether USD",
        "decimals": 6,
        "contract_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
        "contract_address_lowercase": "tr7nhqjekqxgtci8q8zy4pl8otszgjlj6t",
        "token_standard": "TRC-20",
        "is_native": False,
        "coingecko_id": "tether-tron",
        "coinmarketcap_id": 825,
    },
    # Stacks tokens (chain_id: 101)
    {
        "id": 110,
        "chain_id": 101,
        "symbol": "STX",
        "name": "Stacks",
        "decimals": 6,
        "contract_address": None,
        "contract_address_lowercase": None,
        "token_standard": "native",
        "is_native": True,
        "coingecko_id": "blockstack",
        "coinmarketcap_id": 4847,
    },
    # Solana tokens (chain_id: 102)
    {
        "id": 120,
        "chain_id": 102,
        "symbol": "SOL",
        "name": "Solana",
        "decimals": 9,
        "contract_address": None,
        "contract_address_lowercase": None,
        "token_standard": "native",
        "is_native": True,
        "coingecko_id": "solana",
        "coinmarketcap_id": 5426,
    },
    {
        "id": 121,
        "chain_id": 102,
        "symbol": "USDC",
        "name": "USD Coin",
        "decimals": 6,
        "contract_address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "contract_address_lowercase": "epjfwdd5aufqssqem2qn1xzybapjc8g4wegkkzwytdt1v",
        "token_standard": "SPL",
        "is_native": False,
        "coingecko_id": "usd-coin-solana",
        "coinmarketcap_id": 3408,
    },
    # Bitcoin (chain_id: 103)
    {
        "id": 130,
        "chain_id": 103,
        "symbol": "BTC",
        "name": "Bitcoin",
        "decimals": 8,
        "contract_address": None,
        "contract_address_lowercase": None,
        "token_standard": "native",
        "is_native": True,
        "coingecko_id": "bitcoin",
        "coinmarketcap_id": 1,
    },
]


class Seeder(SeederBase):
    def seed(self, table: str):
        have_new_data = False
        for token in TOKENS:
            print(f"Seeding: {token['symbol']} on chain {token['chain_id']}")
            existing = self.session.execute(text(f"SELECT * FROM {table} WHERE id = :id"), {"id": token["id"]}).scalar()
            if not existing:
                print(f"  Adding new token: {token['symbol']} ({token['name']})")
                have_new_data = True
                self.session.execute(
                    text(f"""
                        INSERT INTO {table} (
                            id, chain_id, symbol, name, decimals, contract_address,
                            contract_address_lowercase, token_standard, is_native,
                            coingecko_id, coinmarketcap_id
                        )
                        VALUES (
                            :id, :chain_id, :symbol, :name, :decimals, :contract_address,
                            :contract_address_lowercase, :token_standard, :is_native,
                            :coingecko_id, :coinmarketcap_id
                        )
                    """),
                    token,
                )
        if have_new_data:
            self.session.commit()
        else:
            print(f"No new records to add in '{table}'.")
        self.status(table)
