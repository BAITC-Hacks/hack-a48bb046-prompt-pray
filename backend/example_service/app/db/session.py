from common.db import Database

from ..core.config import settings

db = Database(settings, service_name="example_service")

# Зависимость FastAPI для получения сессии БД
get_session = db.get_session
