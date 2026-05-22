"""Deploy Gemma 4 26B-A4B on Modal — baseline (FP8 weights + FP8 KV cache).

This is the "standard" OSS endpoint for OllyUW. Uses RedHatAI's reference
FP8 quantization of Gemma 4 26B-A4B on L40S (Ada Lovelace, native FP8 E4M3).

The companion file `deploy_gemma4_turboquant.py` runs the longer-context
variant for evals where context length matters.

Both apps share the same HF + vLLM cache volumes, so whichever cold-starts
first pays the weight-download and CUDA-graph-compile cost, and the other
reuses them.

Usage:
    uv run modal deploy src/service_provider/modal/deploy_gemma4_standard.py

After deploy, Modal prints a URL like:
    https://<workspace>--ollyuw-gemma4-standard-serve.modal.run

Set MODAL_STANDARD_BASE_URL to that URL in your .env.
"""

import json
import subprocess

import modal


# ─── Identity ──────────────────────────────────────────────────────────────
APP_NAME = "ollyuw-gemma4-standard"
MODEL_WEIGHTS = "RedHatAI/gemma-4-26B-A4B-it-FP8-Dynamic"  # reference FP8 W8A8, kv_cache_scheme=null
MODEL_REVISION = None  # pin a revision once stable; leave None to use latest
SERVED_MODEL_NAME = "google/gemma-4-26B-A4B-it"  # canonical alias exposed on the API

# ─── vLLM config ───────────────────────────────────────────────────────────
N_GPU = 1
VLLM_PORT = 8000
MINUTES = 60

# CUDA graphs vs faster cold start.
#   False (default) = compile CUDA graphs ⇒ slower cold start, faster steady-state
#   True            = skip compilation     ⇒ faster cold start, ~10-20% slower decode
# Leave False for the demo; flip True during heavy dev iteration.
FAST_BOOT = False

# Context window. L40S (48 GB) − FP8 weights (~27 GB) − CUDA overhead
# leaves ~17 GB for KV cache. FP8 KV (E4M3, native on Ada) easily fits 128 K.
MAX_MODEL_LEN = 131_072


app = modal.App(APP_NAME)

# ─── Cache volumes (shared with the turboquant variant) ────────────────────
# Two-volume split per Modal vLLM best practice:
#   huggingface-cache → no re-download of ~27 GB on cold start
#   vllm-cache        → no recompilation of CUDA graphs on cold start
hf_cache_vol = modal.Volume.from_name("ollyuw-huggingface-cache", create_if_missing=True)
vllm_cache_vol = modal.Volume.from_name("ollyuw-vllm-cache", create_if_missing=True)

# ─── Image ─────────────────────────────────────────────────────────────────
vllm_image = (
    modal.Image.from_registry("nvidia/cuda:12.9.0-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install("vllm==0.21.0")  # transformers resolved automatically
    .env(
        {
            "HF_XET_HIGH_PERFORMANCE": "1",      # faster HF Hub downloads
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "VLLM_LOG_STATS_INTERVAL": "1",      # per-second stats for cost analysis
        }
    )
)


@app.function(
    image=vllm_image,
    gpu="L40S",
    scaledown_window=5 * MINUTES,    # stay warm 5 min between agent steps
    timeout=10 * MINUTES,
    volumes={
        "/root/.cache/huggingface": hf_cache_vol,
        "/root/.cache/vllm": vllm_cache_vol,
    },
)
@modal.concurrent(max_inputs=10)     # vLLM batches; one container handles many requests
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
        "--async-scheduling",                     # overlap scheduling and GPU work
        "--tensor-parallel-size", str(N_GPU),
        "--gpu-memory-utilization", "0.93",
        "--enable-prefix-caching",                # critical for agent loops: reuse system prompt + earlier turns
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
