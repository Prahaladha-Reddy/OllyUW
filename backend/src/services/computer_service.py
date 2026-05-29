from __future__ import annotations

from datetime import datetime, timezone

from src.config import get_settings
from src.models.computer import ComputerRecord, ComputerRuntimeState, ComputerStatus
from src.providers.e2b_provider import E2BDesktopRuntime
from src.repositories.computer_repository import ComputerRepository


def _to_record(row: dict) -> ComputerRecord:
    desktop_host = row.get("desktop_host")
    desktop_port = row.get("desktop_port")
    return ComputerRecord(
        id=row["id"],
        user_id=row["user_id"],
        status=row["status"],
        runtime_state=row.get("runtime_state", "stopped"),
        sandbox_id=row.get("sandbox_id"),
        snapshot_id=row.get("snapshot_id"),
        workspace_path=row.get("workspace_path") or "/home/user/workspace",
        git_enabled=row.get("git_enabled", True),
        desktop_host=desktop_host,
        desktop_port=desktop_port,
        desktop_url=row.get("desktop_url"),
        last_booted_at=row.get("last_booted_at"),
        last_paused_at=row.get("last_paused_at"),
        last_snapshot_at=row.get("last_snapshot_at"),
        error_message=row.get("error_message"),
        last_active=row["last_active"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class ComputerService:
    def __init__(self, computer_repo: ComputerRepository, runtime: E2BDesktopRuntime) -> None:
        self._computers = computer_repo
        self._runtime = runtime

    async def debug_runtime(self, user_id: str) -> dict:
        computer = self.get_or_create(user_id)
        if not computer.sandbox_id:
            return {"error": "no running sandbox"}
        script = """
echo "=== template check ===" && ls /usr/local/bin/start-desktop.sh 2>&1 || echo "script missing"
echo "=== processes ===" && ps aux | grep -E "Xvfb|vnc|websockify|xfce" | grep -v grep || echo "none"
echo "=== desktop log ===" && cat /tmp/desktop.log 2>/dev/null || echo "no log yet"
echo "=== ports ===" && ss -tlnp 2>/dev/null | grep -E "5901|6080" || echo "no ports"
""".strip()
        result = await _to_thread(self._runtime.run_command, computer.sandbox_id, script)
        return {"sandbox_id": computer.sandbox_id, "output": result}

    async def upload_workspace_files(
        self,
        user_id: str,
        files: list[tuple[str, bytes]],
        dest_path: str,
    ) -> list[str]:
        """Write files into the sandbox workspace and take a snapshot.

        files: list of (original_filename, raw_bytes)
        dest_path: desired folder inside workspace, e.g. "submissions/acme/"
        Returns: list of absolute sandbox paths that were written.
        """
        computer = self.get_or_create(user_id)
        if not computer.sandbox_id:
            raise ValueError("computer is not running")

        workspace_root = get_settings().e2b_workspace_path
        # Normalise dest_path: strip leading slash, ensure trailing slash.
        dest_clean = dest_path.strip("/")
        folder = f"{workspace_root}/{dest_clean}" if dest_clean else workspace_root

        written: list[str] = []
        for filename, content in files:
            # Sanitise filename: strip any path component the client may sneak in.
            safe_name = filename.replace("/", "_").replace("..", "_")
            remote_path = f"{folder}/{safe_name}"
            await _to_thread(
                self._runtime.write_workspace_file,
                computer.sandbox_id,
                remote_path,
                content,
            )
            written.append(remote_path)

        # Snapshot so files survive a future sandbox recreation.
        snapshot_id = await _to_thread(
            self._runtime.snapshot,
            computer.sandbox_id,
            f"computer-{computer.id}-latest",
        )
        now = datetime.now(timezone.utc).isoformat()
        self._computers.update(
            computer.id,
            {"snapshot_id": snapshot_id, "last_snapshot_at": now, "last_active": now},
        )

        return written

    async def list_workspace_files(self, user_id: str) -> list[str]:
        computer = self.get_or_create(user_id)
        if not computer.sandbox_id:
            raise ValueError("computer is not running")
        workspace_root = get_settings().e2b_workspace_path
        return await _to_thread(
            self._runtime.list_workspace_files,
            computer.sandbox_id,
            workspace_root,
        )

    def reset_runtime(self, user_id: str) -> ComputerRecord:
        computer = self.get_or_create(user_id)
        row = self._computers.update(
            computer.id,
            {
                "sandbox_id": None,
                "snapshot_id": None,
                "desktop_host": None,
                "desktop_port": None,
                "runtime_state": ComputerRuntimeState.STOPPED.value,
                "error_message": None,
            },
        )
        return _to_record(row)

    def get_or_create(self, user_id: str) -> ComputerRecord:
        row = self._computers.get_by_user(user_id)
        if row is None:
            row = self._computers.create_default(user_id)
        return _to_record(row)

    async def start_runtime(self, user_id: str) -> ComputerRecord:
        computer = self.get_or_create(user_id)
        row = self._computers.update(
            computer.id,
            {"runtime_state": ComputerRuntimeState.STARTING.value, "error_message": None},
        )
        computer = _to_record(row)
        now = datetime.now(timezone.utc).isoformat()
        try:
            s = get_settings()
            agent_env: dict[str, str] = {
                "SESSION_ID": computer.id,
                "OLLYUW_USER_ID": user_id,
                "REDIS_URL": s.redis_url,
                "WORKSPACE": s.e2b_workspace_path,
                "MODAL_TURBO_BASE_URL": s.modal_turbo_base_url,
                "MODAL_API_KEY": s.modal_api_key,
                "MODAL_MODEL": s.modal_model,
                "DEEPSEEK_API_KEY": s.deepseek_api_key,
                "DEEPSEEK_BASE_URL": s.deepseek_base_url,
                "DEEPSEEK_MODEL": s.deepseek_model,
                "MEM0_API_KEY": s.mem0_api_key,
                "PARALLEL_API_KEY": s.parallel_api_key,
                "LANGFUSE_PUBLIC_KEY": s.langfuse_public_key,
                "LANGFUSE_SECRET_KEY": s.langfuse_secret_key,
                "LANGFUSE_BASE_URL": s.langfuse_base_url,
            }
            handle = await _to_thread(
                self._runtime.start,
                computer_id=computer.id,
                user_id=user_id,
                sandbox_id=computer.sandbox_id,
                snapshot_id=computer.snapshot_id,
                agent_env=agent_env,
            )
            row = self._computers.update(
                computer.id,
                {
                    "status": ComputerStatus.ONLINE.value,
                    "runtime_state": ComputerRuntimeState.RUNNING.value,
                    "sandbox_id": handle.sandbox_id,
                    "desktop_host": handle.desktop_host,
                    "desktop_port": handle.desktop_port,
                    "desktop_url": handle.desktop_url,
                    "last_booted_at": now,
                    "last_active": now,
                    "error_message": None,
                },
            )
        except Exception as exc:
            row = self._computers.update(
                computer.id,
                {
                    "status": ComputerStatus.SLEEPING.value,
                    "runtime_state": ComputerRuntimeState.ERROR.value,
                    "error_message": str(exc),
                },
            )
            raise
        return _to_record(row)

    async def pause_runtime(self, user_id: str) -> ComputerRecord:
        computer = self.get_or_create(user_id)
        if not computer.sandbox_id:
            return computer
        # Snapshot before pausing so the filesystem state (workspace files,
        # agent state) is preserved. Without this, only power-off created
        # snapshots, so any files uploaded in a session would be lost if the
        # sandbox ever needed to be recreated from the snapshot.
        snapshot_id = await _to_thread(
            self._runtime.snapshot,
            computer.sandbox_id,
            f"computer-{computer.id}-latest",
        )
        await _to_thread(self._runtime.pause, computer.sandbox_id)
        now = datetime.now(timezone.utc).isoformat()
        row = self._computers.update(
            computer.id,
            {
                "status": ComputerStatus.SLEEPING.value,
                "runtime_state": ComputerRuntimeState.PAUSED.value,
                "snapshot_id": snapshot_id,
                "desktop_host": None,
                "desktop_port": None,
                "last_paused_at": now,
                "last_snapshot_at": now,
                "last_active": now,
                "error_message": None,
            },
        )
        return _to_record(row)

    async def snapshot_runtime(self, user_id: str) -> ComputerRecord:
        computer = self.get_or_create(user_id)
        if not computer.sandbox_id:
            return computer
        snapshot_id = await _to_thread(
            self._runtime.snapshot,
            computer.sandbox_id,
            f"computer-{computer.id}-latest",
        )
        now = datetime.now(timezone.utc).isoformat()
        row = self._computers.update(
            computer.id,
            {
                "snapshot_id": snapshot_id,
                "last_snapshot_at": now,
                "last_active": now,
                "error_message": None,
            },
        )
        return _to_record(row)

    async def power_off_runtime(self, user_id: str) -> ComputerRecord:
        computer = self.get_or_create(user_id)
        if not computer.sandbox_id:
            return computer
        snapshot_id = await _to_thread(
            self._runtime.power_off,
            computer.sandbox_id,
            f"computer-{computer.id}-poweroff",
        )
        now = datetime.now(timezone.utc).isoformat()
        row = self._computers.update(
            computer.id,
            {
                "status": ComputerStatus.SLEEPING.value,
                "runtime_state": ComputerRuntimeState.STOPPED.value,
                "sandbox_id": None,
                "snapshot_id": snapshot_id,
                "desktop_host": None,
                "desktop_port": None,
                "last_snapshot_at": now,
                "last_active": now,
                "error_message": None,
            },
        )
        return _to_record(row)


async def _to_thread(fn, *args, **kwargs):
    import asyncio

    return await asyncio.to_thread(fn, *args, **kwargs)
