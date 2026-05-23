from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.controllers.auth_controller import router as auth_router
from src.controllers.conversation_controller import router as conversation_router
from src.controllers.health_controller import router as health_router
from src.controllers.project_controller import router as project_router
from src.controllers.session_controller import router as session_router
from src.middleware.error_handler import register_error_handlers
from src.middleware.logging_middleware import LoggingMiddleware
from src.providers import redis_provider

logger = logging.getLogger("ollyuw.app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    if settings.langsmith.api_key:
        os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith.api_key)
        os.environ.setdefault("LANGSMITH_ENDPOINT", settings.langsmith.base_url)
        os.environ.setdefault("LANGCHAIN_TRACING_V2", str(settings.langsmith.tracing).lower())
    try:
        yield
    finally:
        await redis_provider.close_pool()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="OllyUW Backend",
        version="0.1.0",
        description="AI underwriting copilot — agent orchestration layer",
        redirect_slashes=False,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.server.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LoggingMiddleware)
    register_error_handlers(app)

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(project_router)
    app.include_router(conversation_router)
    app.include_router(session_router)

    return app
