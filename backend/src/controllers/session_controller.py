from __future__ import annotations

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.dependencies import get_session_service, require_auth
from src.models.session import (
    CreateSessionRequest,
    MessageListResponse,
    MessageResponse,
    SendMessageRequest,
    SessionListResponse,
    SessionResponse,
)
from src.services.session_service import SessionService

logger = logging.getLogger("ollyuw.session")

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[SessionService, Depends(get_session_service)],
) -> SessionListResponse:
    return SessionListResponse(sessions=service.list_sessions(current_user["user_id"]))


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    body: CreateSessionRequest,
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[SessionService, Depends(get_session_service)],
) -> SessionResponse:
    try:
        session = service.create_session(current_user["user_id"], body.title)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return SessionResponse(session=session)


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[SessionService, Depends(get_session_service)],
) -> None:
    service.delete_session(current_user["user_id"], session_id)


@router.get("/{session_id}/messages", response_model=MessageListResponse)
async def list_messages(
    session_id: str,
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[SessionService, Depends(get_session_service)],
) -> MessageListResponse:
    try:
        msgs = service.get_messages(current_user["user_id"], session_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return MessageListResponse(messages=msgs)


@router.post("/{session_id}/messages", response_model=MessageResponse, status_code=201)
async def send_message(
    session_id: str,
    body: SendMessageRequest,
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[SessionService, Depends(get_session_service)],
) -> MessageResponse:
    try:
        msg = await service.send_message(
            current_user["user_id"], session_id, body.text, body.model
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return MessageResponse(message=msg)


@router.get("/{session_id}/stream")
async def stream_session(
    session_id: str,
    request: Request,
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[SessionService, Depends(get_session_service)],
) -> StreamingResponse:
    user_id = current_user["user_id"]

    async def event_generator():
        try:
            async for event in service.stream_session(user_id, session_id):
                if await request.is_disconnected():
                    break
                # SSE keepalive comments are not forwarded to the client as data.
                if event.get("type") == "_keepalive":
                    yield ": keepalive\n\n"
                    continue
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if event.get("type") == "final":
                    break
        except LookupError as exc:
            error_event = {"type": "error", "text": str(exc)}
            yield f"data: {json.dumps(error_event)}\n\n"
        except Exception as exc:
            logger.exception("stream error session=%s", session_id)
            error_event = {"type": "error", "text": "Internal stream error"}
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
