from __future__ import annotations

import threading
from pathlib import Path

from e2b import Sandbox
from src.config import get_settings
from src.models.session import SessionMeta
AGENT_WORKER = Path(__file__).parent.parent.parent.parent / "e2b-template" / "agent" / "worker.py"
AGENT_TOOLS = Path(__file__).parent.parent.parent.parent / "e2b-template" / "agent" / "tools.py"

# In-process registry: sandbox objects can't be serialised, so we keep them here.
_sandboxes: dict[str, Sandbox] = {}
_lock = threading.Lock()


def register(session_id: str, sandbox: Sandbox) -> None:
    with _lock:
        _sandboxes[session_id] = sandbox


def get(session_id: str) -> Sandbox | None:
    with _lock:
        return _sandboxes.get(session_id)


def deregister(session_id: str) -> None:
    with _lock:
        _sandboxes.pop(session_id, None)


def create_sandbox() -> tuple[Sandbox, str]:
    """
    Spin up an E2B sandbox from the configured template.
    Returns (sandbox, sandbox_id).
    """
    settings = get_settings()
    template_id = settings.e2b_template_id
    timeout = settings.e2b_sandbox_timeout

    if template_id != "base":
        sandbox = Sandbox.create(template_id, timeout=timeout)
    else:
        sandbox = Sandbox.create(timeout=timeout)

    sandbox_id: str = getattr(sandbox, "sandbox_id", None) or getattr(sandbox, "sandboxId", "")
    print(f"[e2b] created sandbox {sandbox_id} (idle timeout: {timeout}s)")
    return sandbox, str(sandbox_id)


def extend_timeout(session_id: str, seconds: int | None = None) -> bool:
    """
    Reset the sandbox's idle timer. Call this on every chat message to keep
    long-running conversations alive past the initial timeout.
    """
    sandbox = get(session_id)
    if sandbox is None:
        return False
    if seconds is None:
        seconds = get_settings().e2b_sandbox_timeout
    sandbox.set_timeout(seconds)
    return True


def _build_env(session: SessionMeta, settings=None) -> dict[str, str]:
    if settings is None:
        settings = get_settings()
    return {
        "SESSION_ID": session.session_id,
        "REDIS_URL": settings.redis_url,
        "INPUT_STREAM": session.input_stream,
        "OUTPUT_CHANNEL": session.output_channel,
        "HEARTBEAT_KEY": session.heartbeat_key,
        "WORKSPACE": "/home/user/workspace",
        "MODAL_TURBO_BASE_URL": settings.modal_turbo_base_url,
        "MODAL_STANDARD_BASE_URL": settings.modal_standard_base_url,
        "MODAL_API_KEY": settings.modal_api_key,
        "MODAL_MODEL": settings.modal_model,
        "DEEPSEEK_API_KEY": settings.deepseek_api_key,
        "DEEPSEEK_BASE_URL": settings.deepseek_base_url,
        "DEEPSEEK_MODEL": settings.deepseek_model,
        # LangSmith tracing — worker uses LangChain which reads these from os.environ
        "LANGSMITH_API_KEY": settings.langsmith_api_key,
        "LANGSMITH_ENDPOINT": settings.langsmith_base_url,
        "LANGCHAIN_TRACING_V2": str(settings.langsmith_tracing).lower(),
    }




AGENT_DEPS = ["redis", "langchain-openai", "langchain-core", "python-dotenv"]
WORKER_LOG = "/home/user/worker.log"


def upload_and_start_worker(sandbox: Sandbox, session: SessionMeta) -> None:
    """
    Upload agent code and launch the worker as a detached background process.
    Output goes to /home/user/worker.log inside the sandbox — fetch with read_worker_log().
    We do NOT keep a long-lived HTTP/2 stream open to the sandbox; the worker
    survives independently and communicates with the backend only via Redis.
    """
    sid = session.session_id

    # Install agent deps. Fast no-op once a custom template bakes them in,
    # but required when running against the base E2B image.
    print(f"[{sid}] installing agent deps in sandbox…")
    install = sandbox.commands.run(
        f"python -m pip install --quiet --disable-pip-version-check {' '.join(AGENT_DEPS)}",
        timeout=180,
    )
    if install.exit_code != 0:
        print(f"[{sid}] pip install failed (exit {install.exit_code}):\n{install.stderr}")
        raise RuntimeError(f"Failed to install agent deps: {install.stderr}")
    print(f"[{sid}] deps installed.")

    sandbox.files.write("/home/user/tools.py", AGENT_TOOLS.read_text(encoding="utf-8"))
    sandbox.files.write("/home/user/worker.py", AGENT_WORKER.read_text(encoding="utf-8"))

    # Make sure the workspace exists before launching the worker.
    mk = sandbox.commands.run("mkdir -p /home/user/workspace", timeout=15)
    if mk.exit_code != 0:
        raise RuntimeError(f"Failed to create workspace: {mk.stderr}")

    # Launch the worker as a true background command. E2B's `background=True`
    # returns a CommandHandle immediately without holding the gRPC stream open,
    # so we don't depend on shell tricks like nohup/setsid/disown.
    env = _build_env(session)
    handle = sandbox.commands.run(
        f"python -u /home/user/worker.py > {WORKER_LOG} 2>&1",
        envs=env,
        background=True,
    )
    pid = getattr(handle, "pid", "?")
    print(f"[{sid}] worker started in background (pid={pid}). logs → {WORKER_LOG}")


def read_worker_log(session_id: str, tail_lines: int = 200) -> str:
    """Fetch the worker log from the sandbox for debugging."""
    sandbox = get(session_id)
    if sandbox is None:
        raise KeyError(session_id)
    result = sandbox.commands.run(f"tail -n {tail_lines} {WORKER_LOG} 2>/dev/null || echo '(no log yet)'", timeout=10)
    return result.stdout
