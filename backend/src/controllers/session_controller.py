
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from src.dependencies import require_auth
from src.models.session import SessionStatus, SessionStatusResponse, WorkerLogResponse
from src.providers import e2b_provider
from src.repositories.session_repository import SessionRepository
from src.dependencies import get_session_repo

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/{session_id}/status", response_model=SessionStatusResponse)
async def status(
    session_id: str,
    repo: SessionRepository = Depends(get_session_repo),
    _: dict = Depends(require_auth),
) -> SessionStatusResponse:
    sandbox = await e2b_provider.get(session_id)
    if sandbox is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    alive = await repo.worker_alive(session_id)
    pending = await repo.pending_messages(session_id)
    sandbox_id = getattr(sandbox, "sandbox_id", None) or getattr(sandbox, "sandboxId", "")

    return SessionStatusResponse(
        session_id=session_id,
        sandbox_id=str(sandbox_id),
        worker_alive=alive,
        pending_messages=pending,
        status=SessionStatus.READY if alive else SessionStatus.CREATING,
    )


@router.get("/{session_id}/logs", response_model=WorkerLogResponse)
async def worker_logs(
    session_id: str,
    tail: int = 200,
    _: dict = Depends(require_auth),
) -> WorkerLogResponse:
    sandbox = await e2b_provider.get(session_id)
    if sandbox is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    log = await asyncio.to_thread(e2b_provider.read_worker_log, sandbox, tail)
    return WorkerLogResponse(session_id=session_id, log=log)
