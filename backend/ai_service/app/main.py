from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, Request

from common.app import create_app
from common.auth import token_user_dependency

from .core.config import settings
from .schemas import GenerateRequest, GenerateResponse
from .services.generation import generate_content


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(timeout=settings.OPENAI_TIMEOUT, follow_redirects=False) as client:
        app.state.openai_client = client
        yield


app = create_app(
    title=settings.PROJECT_NAME,
    description="Генерация текстового контента через OpenAI",
    service_name="ai_service",
    settings=settings,
    lifespan=lifespan,
)
get_current_user = token_user_dependency(settings)


@app.post(
    f"{settings.API_V1_STR}/ai/generate",
    response_model=GenerateResponse,
    tags=["generation"],
    dependencies=[Depends(get_current_user)],
)
async def generate(payload: GenerateRequest, request: Request) -> GenerateResponse:
    return await generate_content(payload, request.app.state.openai_client, settings)
