from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from io import BytesIO

from fastapi import HTTPException
from fastapi import UploadFile

from src.models.file import UpdateNodeRequest
from src.services.file_service import FileService


class FakeComputerRepo:
    def __init__(self) -> None:
        self.row = {
            'id': 'computer-1',
            'user_id': 'user-1',
            'status': 'sleeping',
            'last_active': datetime.now(timezone.utc),
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
        }

    def get_by_user(self, user_id: str) -> dict | None:
        return self.row if user_id == self.row['user_id'] else None

    def create_default(self, user_id: str) -> dict:
        self.row = {
            'id': 'computer-1',
            'user_id': user_id,
            'status': 'sleeping',
            'last_active': datetime.now(timezone.utc),
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
        }
        return self.row


class FakeFileRepo:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def list_for_user(self, user_id: str) -> list[dict]:
        return [row for row in self.rows if row['user_id'] == user_id]

    def create_folder(self, **kwargs) -> dict:
        row = {
            **kwargs,
            'id': kwargs['file_id'],
            'original_name': kwargs['name'],
            'storage_path': None,
            'file_type': 'folder',
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
        }
        self.rows.append(row)
        return row

    def create_file(self, **kwargs) -> dict:
        row = {
            **kwargs,
            'id': kwargs['file_id'],
            'original_name': kwargs['name'],
            'file_type': 'file',
            'automation_trigger_id': None,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
        }
        self.rows.append(row)
        return row

    def update_file(self, *, file_id: str, user_id: str, storage_path: str, file_size: int) -> dict:
        for row in self.rows:
            if row['id'] == file_id and row['user_id'] == user_id:
                row['storage_path'] = storage_path
                row['file_size'] = file_size
                row['updated_at'] = datetime.now(timezone.utc)
                return row
        raise AssertionError('file row not found')

    def update_node(self, *, file_id: str, user_id: str, values: dict) -> dict:
        for row in self.rows:
            if row['id'] == file_id and row['user_id'] == user_id:
                row.update(values)
                row['updated_at'] = datetime.now(timezone.utc)
                return row
        raise AssertionError('node row not found')

    def delete_many(self, *, user_id: str, file_ids: list[str]) -> None:
        self.rows = [
            row for row in self.rows
            if not (row['user_id'] == user_id and row['id'] in file_ids)
        ]


def make_upload(name: str, content: bytes) -> UploadFile:
    return UploadFile(filename=name, file=BytesIO(content))


def test_upload_single_file_creates_file_record(monkeypatch) -> None:
    uploads: list[tuple[str, int]] = []
    monkeypatch.setattr(
        'src.services.file_service.storage_provider.upload',
        lambda path, data, content_type='application/octet-stream': uploads.append((path, len(data))),
    )

    service = FileService(FakeComputerRepo(), FakeFileRepo())
    result = asyncio.run(
        service.upload_files(
            user_id='user-1',
            uploads=[make_upload('notes.md', b'hello')],
        )
    )

    assert len(result.files) == 1
    assert result.files[0].file_type == 'file'
    assert result.files[0].name == 'notes.md'
    assert uploads and uploads[0][0].endswith('/notes.md')


def test_upload_folder_tree_creates_nested_folder_rows(monkeypatch) -> None:
    monkeypatch.setattr(
        'src.services.file_service.storage_provider.upload',
        lambda path, data, content_type='application/octet-stream': None,
    )

    repo = FakeFileRepo()
    service = FileService(FakeComputerRepo(), repo)

    result = asyncio.run(
        service.upload_files(
            user_id='user-1',
            uploads=[
                make_upload('report.md', b'report'),
                make_upload('summary.txt', b'summary'),
            ],
            relative_paths=[
                'research/quarterly/report.md',
                'research/quarterly/summary.txt',
            ],
        )
    )

    assert len(result.files) == 2
    folder_names = sorted(row['name'] for row in repo.rows if row['file_type'] == 'folder')
    assert folder_names == ['quarterly', 'research']
    file_names = sorted(row['name'] for row in repo.rows if row['file_type'] == 'file')
    assert file_names == ['report.md', 'summary.txt']


def test_rename_file_copies_storage_and_updates_path(monkeypatch) -> None:
    uploads: list[tuple[str, str]] = []
    deletes: list[list[str]] = []
    monkeypatch.setattr(
        'src.services.file_service.storage_provider.copy',
        lambda from_path, to_path: uploads.append((from_path, to_path)),
    )
    monkeypatch.setattr(
        'src.services.file_service.storage_provider.delete',
        lambda paths: deletes.append(paths),
    )

    repo = FakeFileRepo()
    repo.rows.append(
        {
            'id': 'file-1',
            'user_id': 'user-1',
            'parent_folder_id': None,
            'name': 'notes.md',
            'original_name': 'notes.md',
            'storage_path': 'user-1/computers/computer-1/file-1/notes.md',
            'file_size': 5,
            'file_type': 'file',
            'automation_trigger_id': None,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
        }
    )

    service = FileService(FakeComputerRepo(), repo)
    result = asyncio.run(
        service.update_file('user-1', 'file-1', UpdateNodeRequest(name='renamed.md'))
    )

    assert result.name == 'renamed.md'
    assert uploads == [('user-1/computers/computer-1/file-1/notes.md', 'user-1/computers/computer-1/file-1/renamed.md')]
    assert deletes == [['user-1/computers/computer-1/file-1/notes.md']]


def test_move_folder_into_descendant_is_rejected() -> None:
    repo = FakeFileRepo()
    now = datetime.now(timezone.utc)
    repo.rows.extend(
        [
            {
                'id': 'folder-1',
                'user_id': 'user-1',
                'parent_folder_id': None,
                'name': 'research',
                'original_name': 'research',
                'storage_path': None,
                'file_size': None,
                'file_type': 'folder',
                'automation_trigger_id': None,
                'created_at': now,
                'updated_at': now,
            },
            {
                'id': 'folder-2',
                'user_id': 'user-1',
                'parent_folder_id': 'folder-1',
                'name': 'quarterly',
                'original_name': 'quarterly',
                'storage_path': None,
                'file_size': None,
                'file_type': 'folder',
                'automation_trigger_id': None,
                'created_at': now,
                'updated_at': now,
            },
        ]
    )

    service = FileService(FakeComputerRepo(), repo)

    try:
        asyncio.run(
            service.update_folder('user-1', 'folder-1', UpdateNodeRequest(parent_folder_id='folder-2'))
        )
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == 'A folder cannot be moved into its descendant'
    else:
        raise AssertionError('Expected HTTPException')


def test_delete_folder_removes_descendants_and_storage(monkeypatch) -> None:
    deleted_paths: list[list[str]] = []
    monkeypatch.setattr(
        'src.services.file_service.storage_provider.delete',
        lambda paths: deleted_paths.append(paths),
    )

    repo = FakeFileRepo()
    now = datetime.now(timezone.utc)
    repo.rows.extend(
        [
            {
                'id': 'folder-1',
                'user_id': 'user-1',
                'parent_folder_id': None,
                'name': 'research',
                'original_name': 'research',
                'storage_path': None,
                'file_size': None,
                'file_type': 'folder',
                'automation_trigger_id': None,
                'created_at': now,
                'updated_at': now,
            },
            {
                'id': 'folder-2',
                'user_id': 'user-1',
                'parent_folder_id': 'folder-1',
                'name': 'quarterly',
                'original_name': 'quarterly',
                'storage_path': None,
                'file_size': None,
                'file_type': 'folder',
                'automation_trigger_id': None,
                'created_at': now,
                'updated_at': now,
            },
            {
                'id': 'file-1',
                'user_id': 'user-1',
                'parent_folder_id': 'folder-2',
                'name': 'report.md',
                'original_name': 'report.md',
                'storage_path': 'user-1/computers/computer-1/file-1/report.md',
                'file_size': 10,
                'file_type': 'file',
                'automation_trigger_id': None,
                'created_at': now,
                'updated_at': now,
            },
        ]
    )

    service = FileService(FakeComputerRepo(), repo)
    asyncio.run(service.delete_folder('user-1', 'folder-1'))

    assert deleted_paths == [['user-1/computers/computer-1/file-1/report.md']]
    assert repo.rows == []
