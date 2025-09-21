from sqlalchemy import text

from backend.seeds.seed import SeederBase

CHAINS = [
    {
        "id": 1,
        "name": "eth",
        "name_full": "Ethereum",
        "chain_type": "evm",
        "chain_id": 1,
        "native_symbol": "ETH",
        "explorer_url": "https://etherscan.io",
    },
    {
        "id": 2,
        "name": "polygon",
        "name_full": "Polygon",
        "chain_type": "evm",
        "chain_id": 137,
        "native_symbol": "MATIC",
        "explorer_url": "https://polygonscan.com",
    },
    {
        "id": 3,
        "name": "bsc",
        "name_full": "BNB Smart Chain",
        "chain_type": "evm",
        "chain_id": 56,
        "native_symbol": "BNB",
        "explorer_url": "https://bscscan.com",
    },
    {
        "id": 100,
        "name": "tron",
        "name_full": "Tron",
        "chain_type": "non-evm",
        "chain_id": 728126428,
        "native_symbol": "TRX",
        "explorer_url": "https://tronscan.org",
    },
    {
        "id": 101,
        "name": "stacks",
        "name_full": "Stacks",
        "chain_type": "non-evm",
        "chain_id": 5757,
        "native_symbol": "STX",
        "explorer_url": "https://explorer.hiro.so",
    },
    {
        "id": 102,
        "name": "solana",
        "name_full": "Solana",
        "chain_type": "non-evm",
        "chain_id": 101,
        "native_symbol": "SOL",
        "explorer_url": "https://solscan.io",
    },
    {
        "id": 103,
        "name": "bitcoin",
        "name_full": "Bitcoin",
        "chain_type": "non-evm",
        "chain_id": 0,
        "native_symbol": "BTC",
        "explorer_url": "https://mempool.space",
    },
]


class Seeder(SeederBase):
    def seed(self, table: str):
        have_new_data = False
        for chain in CHAINS:
            print(f"Seeding: {chain['name']} ({chain['native_symbol']})")
            existing = self.session.execute(text(f"SELECT * FROM {table} WHERE id = :id"), {"id": chain["id"]}).scalar()
            print(f"  Existing: {existing}")
            if not existing:
                print(f"  Adding new chain: {chain['name']}")
                have_new_data = True
                self.session.execute(
                    text(f"""
                        INSERT INTO {table} (id, name, name_full, chain_type, chain_id, native_symbol, explorer_url)
                        VALUES (:id, :name, :name_full, :chain_type, :chain_id, :native_symbol, :explorer_url)
                    """),
                    chain
                )
        if have_new_data:
            self.session.commit()
        else:
            print(f"No new records to add in '{table}'.")
        self.status(table)
