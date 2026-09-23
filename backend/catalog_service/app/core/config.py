from common.config import DatabaseSettings


class Settings(DatabaseSettings):
    PROJECT_NAME: str = "Catalog Service"
    DESCRIPTION: str = "Каталог бизнес-задач AI Sana"
    AI_SERVICE_URL: str = "http://localhost:8003"
    AI_TIMEOUT: float = 65.0


settings = Settings()
