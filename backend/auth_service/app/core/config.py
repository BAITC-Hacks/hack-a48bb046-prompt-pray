from common.config import DatabaseSettings


class Settings(DatabaseSettings):
    PROJECT_NAME: str = "Auth Service"
    DESCRIPTION: str = "Регистрация, вход и управление пользователями"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7


settings = Settings()
