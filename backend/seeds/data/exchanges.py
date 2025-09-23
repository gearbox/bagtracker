from sqlalchemy import text

from backend.seeds.seed import SeederBase

DATA = [
    {
        "id": 1,
        "name": "bybit",
        "display_name": "ByBit",
    },
    {
        "id": 2,
        "name": "binance",
        "display_name": "Binance",
    },
    {
        "id": 3,
        "name": "bingx",
        "display_name": "BingX",
    },
    {
        "id": 4,
        "name": "htx",
        "display_name": "Huobi Global (HTX)",
    },
]


class Seeder(SeederBase):
    
    def seed(self, table: str):
        have_new_data = False
        for item in DATA:
            existing = self.session.execute(text(f"SELECT * FROM {table} WHERE id = :id"), {"id": item["id"]}).scalar()
            if not existing:
                self.session.execute(
                    text(f"""
                        INSERT INTO {table} (id, name, display_name) 
                        VALUES (:id, :name, :display_name)
                    """),
                    item
                )
                have_new_data = True
                print(f"  Adding new exchange: {item['name']}")
            else:
                print(f"  Existing: {existing}")
        if have_new_data:
            self.session.commit()
        else:
            print("  No new exchanges to add")
        self.status(table)
