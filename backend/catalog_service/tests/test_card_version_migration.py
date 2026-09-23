import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.card_version_migration import migrate_card_version


async def test_old_cards_keep_content_and_start_at_version_one(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'old-cards.db').as_posix()}")
    try:
        async with engine.begin() as connection:
            await connection.execute(text("CREATE TABLE task_cards (id INTEGER PRIMARY KEY, title TEXT, confirmed_at TEXT)"))
            await connection.execute(text("INSERT INTO task_cards VALUES (1, 'Saved title', '2026-09-23')"))
        await migrate_card_version(engine)
        await migrate_card_version(engine)
        async with engine.begin() as connection:
            assert (await connection.execute(text("SELECT title, confirmed_at, version FROM task_cards"))).one() == (
                "Saved title", "2026-09-23", 1,
            )
            await connection.execute(text("UPDATE task_cards SET version = 5"))
        await engine.dispose()
        await migrate_card_version(engine)
        async with engine.connect() as connection:
            assert (await connection.execute(text("SELECT version FROM task_cards"))).scalar_one() == 5
        for invalid in [0, -1, None]:
            with pytest.raises(IntegrityError):
                async with engine.begin() as connection:
                    await connection.execute(text("UPDATE task_cards SET version = :value"), {"value": invalid})
    finally:
        await engine.dispose()
