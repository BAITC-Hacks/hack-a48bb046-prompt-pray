from common.auth import token_user_dependency

from ..core.config import settings

# Пользователь берётся из access-токена (подпись проверяется общим секретом),
# в auth_service сервис за каждым запросом не ходит.
get_current_user = token_user_dependency(settings)
