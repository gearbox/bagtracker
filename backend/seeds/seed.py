import argparse
from importlib import import_module
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.databases.factory import init_database, get_db_instance
from backend.settings import settings


class SeederBase(ABC):

    def __init__(self, session: Session):
        self.session = session

    @abstractmethod
    def seed(self, table: str):
        pass

    def clear(self, table: str) -> None:
        self.session.execute(text(f"DELETE FROM {table}"))
        self.session.commit()
        print(f"'{table}' table cleared.")
        self.status(table)

    def _count(self, table: str) -> int:
        result = self.session.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
        return result[0] if result else 0

    def status(self, table: str) -> None:
        count = self._count(table)
        print(f"Total records in table '{table}': {count}")

    def process(self, table: str, action_name: str) -> None:
        actions = self.actions()
        if action_name in actions:
            getattr(self, action_name)(table)
        else:
            print(f"Action '{action_name}' not supported. Supported actions: {self.actions_str()}")
            exit(1)

    @staticmethod
    def actions() -> tuple:
        return (
            "seed",
            "clear", 
            "status",
        )

    @staticmethod
    def actions_str() -> str:
        return ", ".join(SeederBase.actions())


def get_seeder_module(table: str):
    try:
        import_path = f"backend.seeds.data.{table}"
        return import_module(import_path)
    except (ModuleNotFoundError, AttributeError) as e:
        print(f"Seeder for table '{table}' not found. Error: {e}")
        exit(1)

def get_args():
    actions_supported_str = SeederBase.actions_str()
    parser = argparse.ArgumentParser(description="Seed chains into the database.")
    parser.add_argument("table", type=str, default="chains", help="Table to operate on: 'chains'")
    parser.add_argument("action", type=str, default="seed", help=f"Action to perform: {actions_supported_str}")
    return parser.parse_args()


if __name__ == "__main__":
    table, action = get_args().table, get_args().action
    module = get_seeder_module(table)
    init_database(settings.db_url, settings.db_type)
    db = get_db_instance()
    print(f"Running action '{action}' on table '{table}'...")
    with db.session() as session:
        seeder = module.Seeder(session)
        seeder.process(table, action)
        print(f"Action '{action}' completed on table '{table}'.")
