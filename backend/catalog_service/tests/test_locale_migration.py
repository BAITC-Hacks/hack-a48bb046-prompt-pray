import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.migrations import migrate_draft_locale
from common.db import Base


@pytest.mark.parametrize("legacy", [True, False])
async def test_locale_upgrade_preserves_content_and_can_be_repeated(tmp_path, legacy):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'upgrade.db').as_posix()}")
    try:
        async with engine.begin() as connection:
            if legacy:
                await connection.execute(text(
                    "CREATE TABLE task_drafts (id VARCHAR(32) PRIMARY KEY, "
                    "business_id VARCHAR(32) NOT NULL, description TEXT NOT NULL)"
                ))
                await connection.execute(text(
                    "CREATE TABLE clarifying_questions (id VARCHAR(32) PRIMARY KEY, "
                    "draft_id VARCHAR(32) REFERENCES task_drafts(id), question TEXT, answer TEXT)"
                ))
                await connection.execute(text(
                    "INSERT INTO task_drafts VALUES ('draft', 'owner', 'Исходное описание')"
                ))
                await connection.execute(text(
                    "INSERT INTO clarifying_questions VALUES ('q', 'draft', 'Сұрақ?', 'Original answer')"
                ))
            else:
                await connection.run_sync(Base.metadata.create_all)

        await migrate_draft_locale(engine)
        await migrate_draft_locale(engine)
        # Reopening the database must retain the upgrade, not just the connection state.
        await engine.dispose()
        async with engine.begin() as connection:
            columns = await connection.run_sync(lambda conn: inspect(conn).get_columns("task_drafts"))
            assert [column["name"] for column in columns].count("locale") == 1
            locale = next(column for column in columns if column["name"] == "locale")
            assert not locale["nullable"]
            assert locale["default"] == "'ru'"
            if legacy:
                assert (await connection.execute(text(
                    "SELECT description, locale FROM task_drafts"
                ))).one() == ("Исходное описание", "ru")
                assert (await connection.execute(text(
                    "SELECT question, answer FROM clarifying_questions"
                ))).one() == ("Сұрақ?", "Original answer")
                await connection.execute(text("UPDATE task_drafts SET locale = 'kk'"))
        await migrate_draft_locale(engine)
        if legacy:
            async with engine.connect() as connection:
                assert (await connection.execute(text("SELECT locale FROM task_drafts"))).scalar_one() == "kk"
            with pytest.raises(IntegrityError):
                async with engine.begin() as connection:
                    await connection.execute(text("UPDATE task_drafts SET locale = 'de'"))
    finally:
        await engine.dispose()
