from common.auth import token_user_dependency

from ..core.config import settings

get_current_user = token_user_dependency(settings)
