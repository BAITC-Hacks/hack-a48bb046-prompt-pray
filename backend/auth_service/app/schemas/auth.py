from pydantic import BaseModel, EmailStr, field_validator
from .user import Username


class LoginRequest(BaseModel):
    # Keep the existing wire field for clients; it accepts either login identifier.
    email: EmailStr | Username
    password: str

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return value.lower() if '@' in value else value


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # срок жизни access-токена, секунды
