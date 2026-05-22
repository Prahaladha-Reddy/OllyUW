"""Deploy Gemma 4 26B-A4B on Modal — long-context variant (192K).

Same FP8 weights + FP8 KV setup as `deploy_gemma4_standard.py`, just with
a larger max_model_len for evals that exercise long underwriting documents.

NOTE: original plan was to use vLLM's TurboQuant K8V4 KV cache, but
`--kv-cache-dtype turboquant_k8v4` is not a real flag in vLLM 0.21.0.
Revisit if/when vLLM ships TurboQuant support.

Usage:
    uv run modal deploy src/service_provider/modal/deploy_gemma4_turboquant.py

After deploy, Modal prints a URL like:
    https://<workspace>--ollyuw-gemma4-turboquant-serve.modal.run

Set MODAL_TURBO_BASE_URL to that URL in your .env.
"""

import json
import subprocess

import modal


# ─── Identity ──────────────────────────────────────────────────────────────
APP_NAME = "ollyuw-gemma4-turboquant"
MODEL_WEIGHTS = "RedHatAI/gemma-4-26B-A4B-it-FP8-Dynamic"  # reference FP8 W8A8, kv_cache_scheme=null
MODEL_REVISION = None  # pin a revision once stable; leave None to use latest
SERVED_MODEL_NAME = "google/gemma-4-26B-A4B-it"  # canonical alias exposed on the API

# ─── vLLM config ───────────────────────────────────────────────────────────
N_GPU = 1
VLLM_PORT = 8000
MINUTES = 60

FAST_BOOT = False  # see deploy_gemma4_standard.py for explanation

# L40S (48 GB) − FP8 weights (~27 GB) leaves ~17 GB for KV cache.
# Gemma uses sliding-window attention (only 1-in-6 layers keep full KV),
# so ~250K fits. Testing showed 240K actual tokens succeeded; try 256K.
MAX_MODEL_LEN = 262_144


app = modal.App(APP_NAME)

# ─── Cache volumes (shared with the standard variant) ──────────────────────
hf_cache_vol = modal.Volume.from_name("ollyuw-huggingface-cache", create_if_missing=True)
vllm_cache_vol = modal.Volume.from_name("ollyuw-vllm-cache", create_if_missing=True)

# ─── Image ─────────────────────────────────────────────────────────────────
vllm_image = (
    modal.Image.from_registry("nvidia/cuda:12.9.0-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install("vllm==0.21.0")
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
    scaledown_window=5 * MINUTES,
    timeout=10 * MINUTES,
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

        # === Performance ===
        "--async-scheduling",
        "--tensor-parallel-size", str(N_GPU),
        "--gpu-memory-utilization", "0.93",
        "--enable-prefix-caching",
        "--enforce-eager" if FAST_BOOT else "--no-enforce-eager",

        # === Memory ===
        # Quantization auto-detected from model config (compressed-tensors FP8 W8A8 dynamic)
        "--kv-cache-dtype", "fp8",                # E4M3, native on L40S (Ada SM_89)
        "--max-model-len", str(MAX_MODEL_LEN),
        "--dtype", "auto",

        # === No multimodal in LLM (images are pre-parsed by a separate VLM) ===
        "--limit-mm-per-prompt",
        f"'{json.dumps({'image': 0, 'video': 0, 'audio': 0})}'",

        # NOTE: --tool-call-parser gemma4 and --reasoning-parser gemma4 are NOT
        # valid in vLLM 0.21.0 (would crash boot). Tool calling for the agent
        # loop is handled at the LangGraph layer for now.
    ]

    print("Starting vLLM:", " ".join(cmd))
    subprocess.Popen(" ".join(cmd), shell=True)
