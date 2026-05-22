from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

AGENT_DIR = Path(__file__).parent.parent.parent / "e2b-template" / "agent"
sys.path.insert(0, str(AGENT_DIR))



class TestTools:
    def setup_method(self):
        import tools as t
        self.tools = t

    def test_list_files_missing_path(self, tmp_path):
        import tools as t
        t.WORKSPACE = tmp_path
        result = t.tool_list_files("nonexistent")
        assert "missing" in result

    def test_write_and_read_file(self, tmp_path):
        import tools as t
        t.WORKSPACE = tmp_path
        t.tool_write_file("hello.txt", "world")
        content = t.tool_read_file("hello.txt")
        assert content == "world"

    def test_path_traversal_blocked(self, tmp_path):
        import tools as t
        t.WORKSPACE = tmp_path
        with pytest.raises(ValueError, match="escapes workspace"):
            t.tool_read_file("../../etc/passwd")

    def test_run_shell_returns_exit_code(self, tmp_path):
        import tools as t
        t.WORKSPACE = tmp_path
        result = t.tool_run_shell("echo hello")
        assert "hello" in result
        assert "[exit_code] 0" in result

    def test_run_shell_nonzero_exit(self, tmp_path):
        import tools as t
        t.WORKSPACE = tmp_path
        result = t.tool_run_shell("exit 1")
        assert "[exit_code] 1" in result



class TestSessionService:
    @pytest.mark.asyncio
    async def test_send_message_unknown_session(self):
        from src.services.session_service import SessionService

        mock_repo = MagicMock()
        mock_repo.get = MagicMock(return_value=None)

        async def async_none(*a, **kw):
            return None

        mock_repo.get = async_none
        service = SessionService(mock_repo, MagicMock())

        with pytest.raises(KeyError):
            await service.send_message("bad-id", "hello")



@pytest.mark.integration
class TestIntegration:
    """
    Requires real E2B_API_KEY, REDIS_URL, MODAL_TURBO_BASE_URL in environment.
    Run with: pytest -m integration
    """

    @pytest.mark.asyncio
    async def test_create_session_and_ping(self):
        from src.providers.redis_provider import ping

        ok = await ping()
        assert ok, "Redis should be reachable"

    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self):
        import asyncio
        from httpx import AsyncClient, ASGITransport
        from src.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/sessions/")
            assert resp.status_code == 201
            session_id = resp.json()["session_id"]

            # Give worker time to start
            await asyncio.sleep(3)

            status_resp = await client.get(f"/sessions/{session_id}/status")
            assert status_resp.status_code == 200
            data = status_resp.json()
            assert "worker_alive" in data
