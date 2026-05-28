from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from src.app import create_app
from src.dependencies import (
    get_auth_service,
    get_computer_service,
    get_connection_service,
    get_file_service,
    get_vault_service,
    require_auth,
)
from src.models.auth import AuthResponse
from src.models.computer import ComputerRecord, ComputerRuntimeState, ComputerStatus
from src.models.connection import ConnectionRecord
from src.models.file import FileRecord, FileType
from src.models.vault import VaultItemRecord, VaultItemType
from src.services.file_service import DownloadedFile


class FakeComputerService:
    def get_or_create(self, user_id: str) -> ComputerRecord:
        now = datetime.now(timezone.utc)
        return ComputerRecord(
            id='computer-1',
            user_id=user_id,
            status=ComputerStatus.SLEEPING,
            runtime_state=ComputerRuntimeState.STOPPED,
            sandbox_id=None,
            snapshot_id='snapshot-1',
            workspace_path='/home/user/workspace',
            git_enabled=True,
            desktop_host=None,
            desktop_port=None,
            desktop_url=None,
            last_booted_at=None,
            last_paused_at=None,
            last_snapshot_at=now,
            error_message=None,
            last_active=now,
            created_at=now,
            updated_at=now,
        )

    async def start_runtime(self, user_id: str) -> ComputerRecord:
        now = datetime.now(timezone.utc)
        return ComputerRecord(
            id='computer-1',
            user_id=user_id,
            status=ComputerStatus.ONLINE,
            runtime_state=ComputerRuntimeState.RUNNING,
            sandbox_id='sandbox-1',
            snapshot_id='snapshot-1',
            workspace_path='/home/user/workspace',
            git_enabled=True,
            desktop_host='desktop.example.com',
            desktop_port=6080,
            desktop_url='https://desktop.example.com',
            last_booted_at=now,
            last_paused_at=None,
            last_snapshot_at=now,
            error_message=None,
            last_active=now,
            created_at=now,
            updated_at=now,
        )

    async def pause_runtime(self, user_id: str) -> ComputerRecord:
        now = datetime.now(timezone.utc)
        return ComputerRecord(
            id='computer-1',
            user_id=user_id,
            status=ComputerStatus.SLEEPING,
            runtime_state=ComputerRuntimeState.PAUSED,
            sandbox_id='sandbox-1',
            snapshot_id='snapshot-1',
            workspace_path='/home/user/workspace',
            git_enabled=True,
            desktop_host=None,
            desktop_port=None,
            desktop_url=None,
            last_booted_at=now,
            last_paused_at=now,
            last_snapshot_at=now,
            error_message=None,
            last_active=now,
            created_at=now,
            updated_at=now,
        )

    async def snapshot_runtime(self, user_id: str) -> ComputerRecord:
        return await self.start_runtime(user_id)

    async def power_off_runtime(self, user_id: str) -> ComputerRecord:
        return self.get_or_create(user_id)


class FakeFileService:
    def list_files(self, user_id: str) -> list[FileRecord]:
        now = datetime.now(timezone.utc)
        return [
            FileRecord(
                id='file-1',
                user_id=user_id,
                parent_folder_id=None,
                name='research',
                storage_path=None,
                file_type=FileType.FOLDER,
                automation_trigger_id=None,
                created_at=now,
                updated_at=now,
            ),
        ]

    def get_file(self, user_id: str, file_id: str) -> FileRecord:
        return self.list_files(user_id)[0]

    def list_folder_children(self, user_id: str, folder_id: str) -> list[FileRecord]:
        return self.list_files(user_id)

    async def download_file(self, user_id: str, file_id: str) -> DownloadedFile:
        return DownloadedFile(
            filename='research.txt',
            media_type='text/plain',
            content=b'hello',
        )


class FakeConnectionService:
    def list_connections(self, user_id: str) -> list[ConnectionRecord]:
        now = datetime.now(timezone.utc)
        return [
            ConnectionRecord(
                id='connection-1',
                user_id=user_id,
                composio_account_id='acct-1',
                provider='google',
                created_at=now,
            ),
        ]


class FakeVaultService:
    def list_items(self, user_id: str) -> list[VaultItemRecord]:
        now = datetime.now(timezone.utc)
        return [
            VaultItemRecord(
                id='vault-1',
                user_id=user_id,
                item_type=VaultItemType.COOKIE,
                key='session-cookie',
                encrypted_data='ciphertext',
                created_at=now,
                updated_at=now,
            ),
        ]


class FakeAuthService:
    async def login(self, email: str, password: str) -> AuthResponse:
        return AuthResponse(
            access_token='access-token',
            refresh_token='refresh-token',
            user_id='user-1',
            email=email,
        )


async def fake_require_auth() -> dict:
    return {'user_id': 'user-1', 'email': 'user@example.com'}


def test_computer_routes_serve_second_computer_domain() -> None:
    app = create_app()
    app.dependency_overrides[require_auth] = fake_require_auth
    app.dependency_overrides[get_computer_service] = FakeComputerService
    app.dependency_overrides[get_file_service] = FakeFileService
    app.dependency_overrides[get_connection_service] = FakeConnectionService
    app.dependency_overrides[get_vault_service] = FakeVaultService

    with TestClient(app) as client:
        computer = client.get('/computer')
        start_runtime = client.post('/computer/runtime/start')
        pause_runtime = client.post('/computer/runtime/pause')
        snapshot_runtime = client.post('/computer/runtime/snapshot')
        power_off_runtime = client.post('/computer/runtime/power-off')
        files = client.get('/computer/files')
        file_detail = client.get('/computer/files/file-1')
        children = client.get('/computer/folders/file-1/children')
        download = client.get('/computer/files/file-1/download')
        connections = client.get('/computer/connections')
        vault = client.get('/computer/vault/items')

    assert computer.status_code == 200
    assert computer.json()['computer']['id'] == 'computer-1'
    assert computer.json()['computer']['runtime_state'] == 'stopped'

    assert start_runtime.status_code == 200
    assert start_runtime.json()['computer']['desktop_url'] == 'https://desktop.example.com'

    assert pause_runtime.status_code == 200
    assert pause_runtime.json()['computer']['runtime_state'] == 'paused'

    assert snapshot_runtime.status_code == 200
    assert snapshot_runtime.json()['computer']['sandbox_id'] == 'sandbox-1'

    assert power_off_runtime.status_code == 200
    assert power_off_runtime.json()['computer']['runtime_state'] == 'stopped'

    assert files.status_code == 200
    assert files.json()['files'][0]['file_type'] == 'folder'

    assert file_detail.status_code == 200
    assert file_detail.json()['file']['id'] == 'file-1'

    assert children.status_code == 200
    assert children.json()['files'][0]['id'] == 'file-1'

    assert download.status_code == 200
    assert download.content == b'hello'
    assert 'attachment;' in download.headers['content-disposition']

    assert connections.status_code == 200
    assert connections.json()['connections'][0]['provider'] == 'google'

    assert vault.status_code == 200
    assert vault.json()['items'][0]['item_type'] == 'cookie'


def test_openapi_exposes_oauth2_password_flow_for_docs() -> None:
    app = create_app()

    with TestClient(app) as client:
        schema = client.get('/openapi.json')

    assert schema.status_code == 200
    security_schemes = schema.json()['components']['securitySchemes']
    bearer_auth = security_schemes['BearerAuth']
    assert bearer_auth['type'] == 'oauth2'
    assert bearer_auth['flows']['password']['tokenUrl'] == '/auth/token'
    assert schema.json()['paths']['/auth/me']['get']['security'] == [{'BearerAuth': []}]


def test_oauth2_token_endpoint_accepts_form_login() -> None:
    app = create_app()
    app.dependency_overrides[get_auth_service] = FakeAuthService

    with TestClient(app) as client:
        response = client.post(
            '/auth/token',
            data={'username': 'user@example.com', 'password': 'secret'},
        )

    assert response.status_code == 200
    assert response.json() == {
        'access_token': 'access-token',
        'token_type': 'bearer',
        'refresh_token': 'refresh-token',
        'user_id': 'user-1',
        'email': 'user@example.com',
    }
