"""Хеширование паролей (bcrypt). bcrypt — CPU-bound, поэтому уходит в поток."""
import asyncio

import bcrypt

# bcrypt учитывает только первые 72 байта пароля
MAX_PASSWORD_BYTES = 72

# Хеш-заглушка: сверяем с ним, если пользователя нет, чтобы время ответа
# не выдавало, зарегистрирован ли email.
_DUMMY_HASH = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt()).decode()


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(_hash, password)


async def verify_password(password: str, hashed: str | None) -> bool:
    """Если `hashed` is None (пользователь не найден), всё равно тратит время на проверку."""
    ok = await asyncio.to_thread(_verify, password, hashed or _DUMMY_HASH)
    return ok and hashed is not None
