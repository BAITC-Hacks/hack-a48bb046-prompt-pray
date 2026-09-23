"""Additive T-17 upgrade; reuse upgrade_draft_locale from the future T-15 revision.

Run after create_all on the current baseline. No user content is rewritten.
"""
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine


def upgrade_draft_locale(connection: Connection) -> None:
    columns = inspect(connection).get_columns("task_drafts")
    if not any(column["name"] == "locale" for column in columns):
        connection.execute(text(
            "ALTER TABLE task_drafts ADD COLUMN locale VARCHAR(2) NOT NULL "
            "DEFAULT 'ru' CONSTRAINT ck_task_drafts_locale CHECK (locale IN ('ru', 'kk', 'en'))"
        ))


async def migrate_draft_locale(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(upgrade_draft_locale)
