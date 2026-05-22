from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.controllers.health_controller import router as health_router
from src.controllers.session_controller import router as session_router
from src.middleware.error_handler import register_error_handlers
from src.middleware.logging_middleware import LoggingMiddleware


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="OllyUW Backend",
        version="0.1.0",
        description="AI underwriting copilot — agent orchestration layer",
        redirect_slashes=False,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LoggingMiddleware)

    register_error_handlers(app)

    app.include_router(health_router)
    app.include_router(session_router)

    return app
