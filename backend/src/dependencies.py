from __future__ import annotations

from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Security
from fastapi.security import OAuth2PasswordBearer
from supabase import Client

from src.providers import redis_provider, supabase_provider
from src.providers.e2b_provider import E2BDesktopRuntime
from src.repositories.computer_repository import ComputerRepository
from src.repositories.connection_repository import ConnectionRepository
from src.repositories.file_repository import FileRepository
from src.repositories.session_repository import SessionRepository
from src.repositories.vault_repository import VaultRepository
from src.services.auth_service import AuthService
from src.services.computer_service import ComputerService
from src.services.connection_service import ConnectionService
from src.services.file_service import FileService
from src.services.session_service import SessionService
from src.services.vault_service import VaultService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/token",
    scheme_name="BearerAuth",
    description="Authenticate with your Supabase email and password to receive a bearer token.",
    auto_error=False,
)


def get_supabase() -> Client:
    return supabase_provider.get_service_client()


def get_redis() -> aioredis.Redis:
    return redis_provider.get_client()


def get_computer_repo(
    db: Annotated[Client, Depends(get_supabase)],
) -> ComputerRepository:
    return ComputerRepository(db)


def get_file_repo(
    db: Annotated[Client, Depends(get_supabase)],
) -> FileRepository:
    return FileRepository(db)


def get_connection_repo(
    db: Annotated[Client, Depends(get_supabase)],
) -> ConnectionRepository:
    return ConnectionRepository(db)


def get_vault_repo(
    db: Annotated[Client, Depends(get_supabase)],
) -> VaultRepository:
    return VaultRepository(db)


def get_auth_service() -> AuthService:
    return AuthService()


def get_computer_service(
    computer_repo: Annotated[ComputerRepository, Depends(get_computer_repo)],
) -> ComputerService:
    return ComputerService(computer_repo, E2BDesktopRuntime())


def get_file_service(
    computer_repo: Annotated[ComputerRepository, Depends(get_computer_repo)],
    file_repo: Annotated[FileRepository, Depends(get_file_repo)],
) -> FileService:
    return FileService(computer_repo, file_repo)


def get_connection_service(
    connection_repo: Annotated[ConnectionRepository, Depends(get_connection_repo)],
) -> ConnectionService:
    return ConnectionService(connection_repo)


def get_vault_service(
    vault_repo: Annotated[VaultRepository, Depends(get_vault_repo)],
) -> VaultService:
    return VaultService(vault_repo)


def get_session_repo(
    db: Annotated[Client, Depends(get_supabase)],
) -> SessionRepository:
    return SessionRepository(db)


def get_session_service(
    session_repo: Annotated[SessionRepository, Depends(get_session_repo)],
    computer_repo: Annotated[ComputerRepository, Depends(get_computer_repo)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
) -> SessionService:
    return SessionService(session_repo, computer_repo, redis)


async def require_auth(
    token: Annotated[str | None, Security(oauth2_scheme)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> dict:
    if not token:
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    return await auth.verify_token(token)
