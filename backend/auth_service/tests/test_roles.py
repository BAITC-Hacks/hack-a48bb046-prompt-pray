from datetime import timedelta
import uuid

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.db.migrations import migrate_user_role
from common.auth import ACCESS_TOKEN, create_token, token_user_dependency
from common.exceptions import UnauthorizedError


async def test_migrate_existing_users_preserves_data_and_is_repeatable():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR(320))"))
            await conn.execute(text("INSERT INTO users VALUES (1, 'old@example.com')"))
        await migrate_user_role(engine)
        await migrate_user_role(engine)
        async with engine.begin() as conn:
            row = (await conn.execute(text("SELECT email, role FROM users"))).one()
            assert tuple(row) == ("old@example.com", "student")
            with pytest.raises(IntegrityError):
                await conn.execute(text("UPDATE users SET role = 'admin'"))
    finally:
        await engine.dispose()


@pytest.mark.parametrize("role", ["business", "student", None, "admin"])
async def test_token_dependency_exposes_and_validates_roles(role):
    token = create_token(
        subject=str(uuid.uuid4()), token_type=ACCESS_TOKEN,
        expires_delta=timedelta(minutes=5), secret=settings.JWT_SECRET_KEY,
        claims={"role": role} if role is not None else {},
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    dependency = token_user_dependency(settings)
    if role == "admin":
        with pytest.raises(UnauthorizedError):
            await dependency(credentials)
    else:
        assert (await dependency(credentials)).role == role
