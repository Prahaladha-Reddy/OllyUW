from __future__ import annotations

from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, Header, HTTPException
from supabase import Client

from src.providers import redis_provider, supabase_provider
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.file_repository import FileRepository
from src.repositories.message_repository import MessageRepository
from src.repositories.project_repository import ProjectRepository
from src.repositories.session_repository import SessionRepository
from src.services.auth_service import AuthService
from src.services.conversation_service import ConversationService
from src.services.file_service import FileService
from src.services.project_service import ProjectService
from src.services.session_service import SessionService




def get_supabase() -> Client:
    return supabase_provider.get_service_client()


def get_redis() -> aioredis.Redis:
    return redis_provider.get_client()




def get_project_repo(
    db: Annotated[Client, Depends(get_supabase)],
) -> ProjectRepository:
    return ProjectRepository(db)


def get_file_repo(
    db: Annotated[Client, Depends(get_supabase)],
) -> FileRepository:
    return FileRepository(db)


def get_conversation_repo(
    db: Annotated[Client, Depends(get_supabase)],
) -> ConversationRepository:
    return ConversationRepository(db)


def get_message_repo(
    db: Annotated[Client, Depends(get_supabase)],
) -> MessageRepository:
    return MessageRepository(db)


def get_session_repo(
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
) -> SessionRepository:
    return SessionRepository(redis)




def get_auth_service() -> AuthService:
    return AuthService()


def get_project_service(
    project_repo: Annotated[ProjectRepository, Depends(get_project_repo)],
    file_repo: Annotated[FileRepository, Depends(get_file_repo)],
    conversation_repo: Annotated[ConversationRepository, Depends(get_conversation_repo)],
) -> ProjectService:
    return ProjectService(project_repo, file_repo, conversation_repo)


def get_file_service(
    project_repo: Annotated[ProjectRepository, Depends(get_project_repo)],
    file_repo: Annotated[FileRepository, Depends(get_file_repo)],
) -> FileService:
    return FileService(project_repo, file_repo)


def get_conversation_service(
    project_repo: Annotated[ProjectRepository, Depends(get_project_repo)],
    conversation_repo: Annotated[ConversationRepository, Depends(get_conversation_repo)],
) -> ConversationService:
    return ConversationService(project_repo, conversation_repo)


def get_session_service(
    conversation_repo: Annotated[ConversationRepository, Depends(get_conversation_repo)],
    file_repo: Annotated[FileRepository, Depends(get_file_repo)],
    message_repo: Annotated[MessageRepository, Depends(get_message_repo)],
    session_repo: Annotated[SessionRepository, Depends(get_session_repo)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
) -> SessionService:
    return SessionService(
        conversation_repo=conversation_repo,
        file_repo=file_repo,
        message_repo=message_repo,
        session_repo=session_repo,
        redis=redis,
    )




async def require_auth(
    authorization: str | None = Header(None),
    auth: AuthService = Depends(get_auth_service),
) -> dict:
    """Validates the Bearer token and returns {user_id, email}."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    return await auth.verify_token(authorization[7:])
