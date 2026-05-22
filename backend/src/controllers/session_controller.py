from __future__ import annotations

import logging
import traceback
from typing import Annotated, AsyncGenerator

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

logger = logging.getLogger("ollyuw.sessions")

from src.models.session import (
    ChatRequest,
    ChatResponse,
    CreateSessionResponse,
    FilesResponse,
    SessionStatusResponse,
)
from src.providers import redis_provider
from src.repositories.session_repository import SessionRepository
from src.services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])



def get_redis() -> aioredis.Redis:
    return redis_provider.get_client()


def get_repo(redis: Annotated[aioredis.Redis, Depends(get_redis)]) -> SessionRepository:
    return SessionRepository(redis)


def get_service(
    repo: Annotated[SessionRepository, Depends(get_repo)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
) -> SessionService:
    return SessionService(repo, redis)



@router.post("", response_model=CreateSessionResponse, status_code=201)
async def create_session(
    service: Annotated[SessionService, Depends(get_service)],
) -> CreateSessionResponse:
    try:
        return await service.create_session()
    except Exception as exc:
        logger.error("create_session failed:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{session_id}/chat", response_model=ChatResponse)
async def chat(
    session_id: str,
    request: ChatRequest,
    service: Annotated[SessionService, Depends(get_service)],
) -> ChatResponse:
    try:
        return await service.send_message(session_id, request.message)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{session_id}/stream")
async def stream(
    session_id: str,
    service: Annotated[SessionService, Depends(get_service)],
) -> StreamingResponse:
    try:
        generator: AsyncGenerator[str, None] = service.stream_events(session_id)
        # Validate session exists before returning the streaming response
        await service.get_status(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    return StreamingResponse(generator, media_type="text/event-stream")


@router.get("/{session_id}/status", response_model=SessionStatusResponse)
async def status(
    session_id: str,
    service: Annotated[SessionService, Depends(get_service)],
) -> SessionStatusResponse:
    try:
        return await service.get_status(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")


@router.get("/{session_id}/files", response_model=FilesResponse)
async def files(
    session_id: str,
    service: Annotated[SessionService, Depends(get_service)],
) -> FilesResponse:
    try:
        return await service.list_files(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/{session_id}/logs")
async def worker_logs(session_id: str, tail: int = 200) -> dict:
    """Fetch the agent worker's log file from inside the sandbox."""
    from src.providers import e2b_provider
    try:
        text = e2b_provider.read_worker_log(session_id, tail_lines=tail)
        return {"session_id": session_id, "log": text}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
