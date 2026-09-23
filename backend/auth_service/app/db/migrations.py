"""Additive schema upgrade for databases created before user roles existed."""

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine


async def migrate_user_role(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        columns = await connection.run_sync(lambda conn: inspect(conn).get_columns("users"))
        if not any(column["name"] == "role" for column in columns):
            await connection.execute(text(
                "ALTER TABLE users ADD COLUMN role VARCHAR(16) NOT NULL "
                "DEFAULT 'student' CHECK (role IN ('business', 'student'))"
            ))
