"""Versioned catalog schema upgrades, shared by startup and the CLI."""
import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text


def upgrade_connection(connection):
    # Serialize upgrades across PostgreSQL service workers, including first startup.
    if connection.dialect.name == "postgresql":
        connection.execute(text("SELECT pg_advisory_xact_lock(734190215)"))
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).with_name("migrations")))
    config.attributes["connection"] = connection
    command.upgrade(config, "head")


async def upgrade(engine):
    async with engine.begin() as connection:
        await connection.run_sync(upgrade_connection)


async def main():
    from .session import db

    try:
        await db.wait_until_ready()
        await upgrade(db.engine)
    finally:
        await db.dispose()


if __name__ == "__main__":
    asyncio.run(main())
