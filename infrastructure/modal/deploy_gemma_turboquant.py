import json
import subprocess

import modal
APP_NAME = "ollyuw-gemma4-turboquant"
MODEL_WEIGHTS = "RedHatAI/gemma-4-26B-A4B-it-FP8-Dynamic" 
MODEL_REVISION = None  
SERVED_MODEL_NAME = "google/gemma-4-26B-A4B-it"  
N_GPU = 1
VLLM_PORT = 8000
MINUTES = 60

FAST_BOOT = False 
MAX_MODEL_LEN = 262_144


app = modal.App(APP_NAME)

hf_cache_vol = modal.Volume.from_name("ollyuw-huggingface-cache", create_if_missing=True)
vllm_cache_vol = modal.Volume.from_name("ollyuw-vllm-cache", create_if_missing=True)

vllm_image = (
    modal.Image.from_registry("nvidia/cuda:12.9.0-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install("vllm==0.21.0")
    .run_commands(
        "apt-get update && apt-get install -y --no-install-recommends curl && "
        "mkdir -p /opt && "
        "curl -fsSL -o /opt/tool_chat_template_gemma4.jinja "
        "https://raw.githubusercontent.com/vllm-project/vllm/main/examples/tool_chat_template_gemma4.jinja && "
        "test -s /opt/tool_chat_template_gemma4.jinja"
    )
    .env(
        {
            "HF_XET_HIGH_PERFORMANCE": "1",
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "VLLM_LOG_STATS_INTERVAL": "1",
        }
    )
)


@app.function(
    image=vllm_image,
    gpu="L40S",
    scaledown_window=20 * MINUTES,
    timeout=30 * MINUTES,
    volumes={
        "/root/.cache/huggingface": hf_cache_vol,
        "/root/.cache/vllm": vllm_cache_vol,
    },
)
@modal.concurrent(max_inputs=10)
@modal.web_server(port=VLLM_PORT, startup_timeout=10 * MINUTES)
def serve() -> None:
    cmd = [
        "vllm", "serve", MODEL_WEIGHTS,
        *( ["--revision", MODEL_REVISION] if MODEL_REVISION else []),
        "--served-model-name", SERVED_MODEL_NAME, "llm",
        "--host", "0.0.0.0",
        "--port", str(VLLM_PORT),
        "--uvicorn-log-level=info",

        "--async-scheduling",
        "--tensor-parallel-size", str(N_GPU),
        "--gpu-memory-utilization", "0.93",
        "--enable-prefix-caching",
        "--enforce-eager" if FAST_BOOT else "--no-enforce-eager",

        "--kv-cache-dtype", "fp8",
        "--max-model-len", str(MAX_MODEL_LEN),
        "--dtype", "auto",

        "--enable-auto-tool-choice",
        "--tool-call-parser", "gemma4",
        "--reasoning-parser", "gemma4",
        "--chat-template", "/opt/tool_chat_template_gemma4.jinja",

        "--limit-mm-per-prompt",
        f"'{json.dumps({'image': 0, 'video': 0, 'audio': 0})}'",

    ]

    print("Starting vLLM:", " ".join(cmd))
    subprocess.Popen(" ".join(cmd), shell=True)