from common.db import Database

from ..core.config import settings

db = Database(settings, service_name="catalog_service")
get_session = db.get_session
