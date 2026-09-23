"""T-18 additive upgrade, to be called from a versioned T-15 revision."""
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine


def upgrade_card_version(connection: Connection) -> None:
    if not any(column["name"] == "version" for column in inspect(connection).get_columns("task_cards")):
        connection.execute(text(
            "ALTER TABLE task_cards ADD COLUMN version INTEGER NOT NULL DEFAULT 1 "
            "CONSTRAINT ck_task_cards_version CHECK (version >= 1)"
        ))


async def migrate_card_version(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(upgrade_card_version)
