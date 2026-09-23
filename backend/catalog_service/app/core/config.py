from common.config import DatabaseSettings


class Settings(DatabaseSettings):
    PROJECT_NAME: str = "Catalog Service"
    DESCRIPTION: str = "Каталог бизнес-задач, отклики и решения бизнеса"


settings = Settings()
