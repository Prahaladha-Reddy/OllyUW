from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import StreamingResponse

from src.dependencies import (
    get_conversation_service,
    get_file_service,
    get_session_service,
    require_auth,
)
from src.models.conversation import (
    ConversationDetail,
    ConversationsListResponse,
    CreateConversationRequest,
)
from src.models.file import UploadFilesResponse
from src.models.message import (
    MessagesListResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from src.services.file_service import FileService
from src.services.conversation_service import ConversationService
from src.services.session_service import SessionService

router = APIRouter(prefix="/projects/{project_id}/conversations", tags=["conversations"])




@router.post("", response_model=ConversationDetail, status_code=201)
async def create_conversation(
    project_id: str,
    body: CreateConversationRequest,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    current_user: Annotated[dict, Depends(require_auth)],
) -> ConversationDetail:
    return await service.create(current_user["user_id"], project_id, body.title)


@router.get("", response_model=ConversationsListResponse)
async def list_conversations(
    project_id: str,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    current_user: Annotated[dict, Depends(require_auth)],
) -> ConversationsListResponse:
    items = await service.list_for_project(current_user["user_id"], project_id)
    return ConversationsListResponse(conversations=items)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    project_id: str,
    conversation_id: str,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    current_user: Annotated[dict, Depends(require_auth)],
) -> ConversationDetail:
    return await service.get(current_user["user_id"], project_id, conversation_id)


@router.delete("/{conversation_id}")
async def delete_conversation(
    project_id: str,
    conversation_id: str,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    current_user: Annotated[dict, Depends(require_auth)],
) -> Response:
    await service.delete(current_user["user_id"], project_id, conversation_id)
    return Response(status_code=204)



@router.get("/{conversation_id}/messages", response_model=MessagesListResponse)
async def list_messages(
    project_id: str,
    conversation_id: str,
    service: Annotated[SessionService, Depends(get_session_service)],
    current_user: Annotated[dict, Depends(require_auth)],
) -> MessagesListResponse:
    """Persistent chat history. Use this for the initial render."""
    return await service.list_messages(current_user["user_id"], project_id, conversation_id)


@router.post("/{conversation_id}/messages", response_model=SendMessageResponse, status_code=202)
async def send_message(
    project_id: str,
    conversation_id: str,
    body: SendMessageRequest,
    service: Annotated[SessionService, Depends(get_session_service)],
    current_user: Annotated[dict, Depends(require_auth)],
) -> SendMessageResponse:
    """
    Send a user message. Lazily spins up the sandbox + uploads project files on
    the first call. Returns the persisted user message plus the Redis stream id
    the client can correlate with `/stream` events.
    """
    return await service.send_message(
        current_user["user_id"], project_id, conversation_id, body.text,
    )


@router.post("/{conversation_id}/files", response_model=UploadFilesResponse, status_code=202)
async def upload_files_to_conversation(
    project_id: str,
    conversation_id: str,
    file_service: Annotated[FileService, Depends(get_file_service)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
    current_user: Annotated[dict, Depends(require_auth)],
    files: list[UploadFile] = File(description="One or more files to attach to this conversation"),
) -> UploadFilesResponse:
    """
    Upload files mid-conversation. Saves to Supabase and immediately pushes
    to the running sandbox if one is already active for this conversation.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    result = await file_service.upload(
        user_id=current_user["user_id"],
        project_id=project_id,
        uploads=files,
    )
    await session_service.push_files_to_sandbox(
        user_id=current_user["user_id"],
        project_id=project_id,
        conversation_id=conversation_id,
        file_records=result.files,
    )
    return result


@router.get("/{conversation_id}/stream")
async def stream_events(
    project_id: str,
    conversation_id: str,
    service: Annotated[SessionService, Depends(get_session_service)],
    current_user: Annotated[dict, Depends(require_auth)],
) -> StreamingResponse:
    """
    SSE stream of live agent events for this conversation:
    model_delta, tool_call, tool_result, final, sse_heartbeat.
    """
    generator = service.stream(current_user["user_id"], project_id, conversation_id)
    return StreamingResponse(generator, media_type="text/event-stream")
