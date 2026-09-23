from fastapi import APIRouter, Depends

from common.auth import TokenUser

from ...schemas.status import ServiceStatus
from ..deps import get_current_user

router = APIRouter()


@router.get("/status", response_model=ServiceStatus)
async def catalog_status(_: TokenUser = Depends(get_current_user)) -> ServiceStatus:
    """Маршрут для проверки защищённого прохода через gateway."""
    return ServiceStatus(status="ready")
