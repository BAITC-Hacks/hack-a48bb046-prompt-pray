import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from ..core.security import MAX_PASSWORD_BYTES

Username = Annotated[str, Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")]


class UserCreate(BaseModel):
    email: EmailStr
    username: Username
    password: str = Field(min_length=8)
    role: Literal["business", "student"] = "student"

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("password")
    @classmethod
    def _check_password(cls, value: str) -> str:
        if len(value.encode()) > MAX_PASSWORD_BYTES:
            raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes")
        return value


class UserUpdate(BaseModel):
    username: Username | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    username: str
    is_active: bool
    is_admin: bool
    role: Literal["business", "student"]
    created_at: datetime
