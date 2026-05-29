from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.controllers.auth_controller import router as auth_router
from src.controllers.computer_controller import router as computer_router
from src.controllers.connection_controller import router as connection_router
from src.controllers.file_controller import router as file_router
from src.controllers.health_controller import router as health_router
from src.controllers.session_controller import router as session_router
from src.controllers.vault_controller import router as vault_router
from src.middleware.error_handler import register_error_handlers
from src.middleware.logging_middleware import LoggingMiddleware
from src.providers import redis_provider

logger = logging.getLogger("olly.app")


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
        title="Olly Backend",
        version="0.1.0",
        description="Persistent second-computer orchestration layer.",
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
    app.include_router(computer_router)
    app.include_router(file_router)
    app.include_router(connection_router)
    app.include_router(vault_router)
    app.include_router(session_router)

    return app
