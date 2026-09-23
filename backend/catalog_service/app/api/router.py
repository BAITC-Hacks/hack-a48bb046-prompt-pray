from fastapi import APIRouter

from .endpoints import status

api_router = APIRouter()
api_router.include_router(status.router, prefix="/catalog", tags=["catalog"])
