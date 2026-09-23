from fastapi import APIRouter

from .routes import proxy

api_router = APIRouter()
api_router.include_router(proxy.router)
