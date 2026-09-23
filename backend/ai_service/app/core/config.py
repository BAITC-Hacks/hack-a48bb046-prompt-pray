from pydantic import Field, SecretStr

from common.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    PROJECT_NAME: str = "AI Service"
    OPENAI_API_KEY: SecretStr = SecretStr("")
    OPENAI_MODEL: str = Field(default="gpt-6-astra", min_length=1)
    OPENAI_TIMEOUT: float = Field(default=60.0, gt=0, le=300)
    OPENAI_MAX_OUTPUT_TOKENS: int = Field(default=2048, ge=16, le=32768)


settings = Settings()
