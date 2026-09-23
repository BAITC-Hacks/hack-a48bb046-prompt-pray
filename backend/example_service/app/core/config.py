from common.config import DatabaseSettings


class Settings(DatabaseSettings):
    PROJECT_NAME: str = "Example Service"
    DESCRIPTION: str = "Пример сервиса с CRUD — копируйте его как основу для новых сервисов"


settings = Settings()
