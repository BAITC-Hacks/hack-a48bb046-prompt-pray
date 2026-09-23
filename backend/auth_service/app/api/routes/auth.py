from fastapi import APIRouter, Depends, status

from ...schemas.auth import LoginRequest, RefreshRequest, TokenPair
from ...schemas.user import UserCreate, UserRead
from ...services.auth import AuthService
from ..deps import get_auth_service

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, service: AuthService = Depends(get_auth_service)):
    return await service.register(data)


@router.post("/login", response_model=TokenPair)
async def login(data: LoginRequest, service: AuthService = Depends(get_auth_service)):
    user = await service.authenticate(data.email, data.password)
    return service.issue_tokens(user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(data: RefreshRequest, service: AuthService = Depends(get_auth_service)):
    return await service.refresh(data.refresh_token)
