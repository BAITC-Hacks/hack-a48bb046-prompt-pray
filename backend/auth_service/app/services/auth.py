import uuid
from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import ACCESS_TOKEN, REFRESH_TOKEN, create_token, decode_token
from common.exceptions import ConflictError, UnauthorizedError

from ..core.config import settings
from ..core.security import hash_password, verify_password
from ..models import User
from ..repositories.user import UserRepository
from ..schemas.auth import TokenPair
from ..schemas.user import UserCreate


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)

    async def register(self, data: UserCreate) -> User:
        if await self.users.get_by_email(data.email):
            raise ConflictError("Email already registered", code="email_taken")
        if await self.users.get_by_username(data.username):
            raise ConflictError("Username already taken", code="username_taken")

        user = self.users.add(
            User(
                email=data.email,
                username=data.username,
                hashed_password=await hash_password(data.password),
                role=data.role,
            )
        )
        try:
            await self.session.commit()
        except IntegrityError:  # гонка: тот же email/username занял параллельный запрос
            await self.session.rollback()
            raise ConflictError("Email or username already registered", code="user_exists")
        return user

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.users.get_by_email(email)
        password_ok = await verify_password(password, user.hashed_password if user else None)
        # Одинаковый ответ для «нет пользователя» и «неверный пароль»
        if not user or not password_ok or not user.is_active:
            raise UnauthorizedError("Incorrect email or password", code="invalid_credentials")
        return user

    async def refresh(self, refresh_token: str) -> TokenPair:
        payload = decode_token(
            refresh_token,
            secret=settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
            token_type=REFRESH_TOKEN,
        )
        try:
            user = await self.users.get(uuid.UUID(payload["sub"]))
        except ValueError:
            user = None
        if not user or not user.is_active:
            raise UnauthorizedError("User is not available", code="invalid_token")
        return self.issue_tokens(user)

    @staticmethod
    def issue_tokens(user: User) -> TokenPair:
        common = dict(secret=settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        access_ttl = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access = create_token(
            subject=str(user.id),
            token_type=ACCESS_TOKEN,
            expires_delta=access_ttl,
            claims={"email": user.email, "is_admin": user.is_admin, "role": user.role.value},
            **common,
        )
        refresh = create_token(
            subject=str(user.id),
            token_type=REFRESH_TOKEN,
            expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            **common,
        )
        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=int(access_ttl.total_seconds()),
        )
