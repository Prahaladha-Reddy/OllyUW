"""
Cost + latency benchmark for the Modal OSS deployment.

Usage:
    uv run python -m src.oss_deployment.benchmark [--mode turbo|standard] [--runs N]

Outputs a markdown table:
    Scenario | Input Tok | Output Tok | TTFT (s) | Latency (s) | Tok/s | GPU $/req

Pricing reference: Modal L40S @ $1.922/hr = $0.000534/s per GPU
vLLM /metrics endpoint is on the same base URL — no extra infra needed.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from statistics import mean, median

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ── Pricing ──────────────────────────────────────────────────────────────────
L40S_COST_PER_SECOND = 1.922 / 3600  # $0.000534/s

# ── Test scenarios (realistic underwriting inputs) ────────────────────────────
SCENARIOS = [
    {
        "name": "Short / quote check",
        "messages": [
            {
                "role": "user",
                "content": (
                    "An AI startup sells a SaaS risk-scoring API. ARR $2M, "
                    "10 enterprise customers, SOC 2 Type II certified, no prior claims. "
                    "Provide a 2-sentence risk summary and suggested premium range for "
                    "a $5M Tech E&O + Cyber policy."
                ),
            }
        ],
        "max_tokens": 200,
    },
    {
        "name": "Medium / policy analysis",
        "messages": [
            {
                "role": "user",
                "content": (
                    "You are an underwriting copilot. Analyse the following AI company "
                    "submission and identify the top 5 risk factors, coverage gaps, and "
                    "recommended exclusions.\n\n"
                    "Company: NeuralEdge Inc.\n"
                    "Product: Autonomous contract review software deployed inside Fortune 500 legal teams.\n"
                    "Revenue: $8M ARR, growing 180% YoY.\n"
                    "Customers: 35 enterprises, avg contract $230k/yr.\n"
                    "Technology: Fine-tuned LLM on proprietary legal corpus. Outputs are reviewed by "
                    "human attorneys before filing.\n"
                    "Data handling: Processes privileged attorney-client communications; "
                    "stores data on AWS with AES-256 at rest, TLS 1.3 in transit.\n"
                    "Security posture: SOC 2 Type II (last audit 14 months ago), bug bounty program, "
                    "no known breaches, one near-miss phishing incident in Q3.\n"
                    "Prior insurance: $2M Cyber, $1M E&O — no claims in 3 years.\n"
                    "Requested: $10M Cyber + $5M Tech E&O + $2M MPL.\n\n"
                    "Provide structured analysis with risk score (1-10) per dimension."
                ),
            }
        ],
        "max_tokens": 800,
    },
    {
        "name": "Long / full underwriting report",
        "messages": [
            {
                "role": "user",
                "content": (
                    "You are OllyUW, an AI underwriting copilot specialising in AI-company insurance. "
                    "Generate a full underwriting report for the following submission. "
                    "Include: Executive Summary, Risk Dimensions (technology risk, data/privacy risk, "
                    "operational risk, financial risk, regulatory risk), Coverage Recommendations "
                    "(limits, retentions, key exclusions, endorsements), Pricing Guidance "
                    "(loss-cost model, rate adequacy commentary), and Open Information Requests.\n\n"
                    + "\n".join(
                        [
                            "Company: Synaptix AI",
                            "Headquarters: San Francisco, CA",
                            "Founded: 2021",
                            "Business: AI-powered medical imaging diagnostic tool. FDA 510(k) cleared "
                            "for radiology workflow assistance (not autonomous diagnosis).",
                            "Revenue: $14M ARR; $4M in 2023, $9M in 2024, on track for $20M in 2025.",
                            "Customers: 42 hospital systems, 8 radiology groups; avg contract $335k/yr.",
                            "Geography: US only; 3 contracts pending in EU (GDPR + MDR compliance TBD).",
                            "Headcount: 85 FTE; 28 engineers, 12 ML researchers, 6 regulatory/QA.",
                            "Technology stack: PyTorch models hosted on AWS (us-east-1, us-west-2), "
                            "HIPAA BAAs in place with AWS and all cloud sub-processors.",
                            "Data: Trains on de-identified DICOM datasets licensed from 6 hospital "
                            "partners. PHI handling: zero PHI stored post-inference; audit logs retained "
                            "7 years per HIPAA.",
                            "Security: SOC 2 Type II (audited 4 months ago), HITRUST CSF v11 "
                            "certification in progress, penetration test Q1 2025 (3 medium findings, "
                            "all remediated), no breaches.",
                            "Regulatory: FDA 510(k) clearance (K241892); post-market surveillance plan "
                            "active. EU MDR Class IIa application Q4 2025.",
                            "Litigation: One demand letter from a radiology group alleging missed "
                            "nodule (settled pre-suit for $85k, not reported to prior insurer — "
                            "needs clarification).",
                            "Prior coverage: $5M Cyber (Chubb), $3M Tech E&O (Beazley), $1M MPL "
                            "(The Doctors Company) — all expiring.",
                            "Requested: $15M Cyber, $10M Tech E&O, $5M MPL, $2M D&O.",
                            "Broker: Lockton San Francisco, contact Jane Doe.",
                        ]
                    )
                ),
            }
        ],
        "max_tokens": 2000,
    },
]


@dataclass
class RequestResult:
    scenario: str
    input_tokens: int
    output_tokens: int
    ttft_s: float
    total_s: float
    tokens_per_s: float
    gpu_cost_usd: float
    error: str = ""


def stream_request(client: OpenAI, model: str, messages: list, max_tokens: int) -> RequestResult:
    """Send a streaming chat completion and measure TTFT + total latency."""
    t0 = time.perf_counter()
    ttft_s = 0.0
    input_tokens = 0
    output_tokens = 0
    first_chunk = True

    try:
        with client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            stream=True,
            stream_options={"include_usage": True},
        ) as stream:
            for chunk in stream:
                if first_chunk and chunk.choices and chunk.choices[0].delta.content:
                    ttft_s = time.perf_counter() - t0
                    first_chunk = False
                if chunk.usage:
                    input_tokens = chunk.usage.prompt_tokens
                    output_tokens = chunk.usage.completion_tokens

    except Exception as exc:
        elapsed = time.perf_counter() - t0
        return RequestResult(
            scenario="", input_tokens=0, output_tokens=0,
            ttft_s=elapsed, total_s=elapsed, tokens_per_s=0,
            gpu_cost_usd=0, error=str(exc),
        )

    total_s = time.perf_counter() - t0
    tokens_per_s = output_tokens / total_s if total_s > 0 else 0
    gpu_cost_usd = total_s * L40S_COST_PER_SECOND

    return RequestResult(
        scenario="",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        ttft_s=ttft_s,
        total_s=total_s,
        tokens_per_s=tokens_per_s,
        gpu_cost_usd=gpu_cost_usd,
    )


def fetch_vllm_metrics(base_url: str) -> dict[str, float]:
    """Pull key percentiles from vLLM's Prometheus /metrics endpoint."""
    url = base_url.rstrip("/")
    # strip /v1 suffix if present
    if url.endswith("/v1"):
        url = url[:-3]
    try:
        req = urllib.request.urlopen(f"{url}/metrics", timeout=10)
        body = req.read().decode()
    except Exception as exc:
        print(f"  [warn] could not fetch /metrics: {exc}", file=sys.stderr)
        return {}

    stats: dict[str, float] = {}
    for line in body.splitlines():
        if line.startswith("#"):
            continue
        # grab _sum and _count for key histograms
        for key in (
            "vllm:e2e_request_latency_seconds_sum",
            "vllm:e2e_request_latency_seconds_count",
            "vllm:time_to_first_token_seconds_sum",
            "vllm:time_to_first_token_seconds_count",
            "vllm:time_per_output_token_seconds_sum",
            "vllm:time_per_output_token_seconds_count",
            "vllm:num_generation_tokens_total",
            "vllm:num_prompt_tokens_total",
        ):
            if line.startswith(key + " ") or line.startswith(key + "{"):
                try:
                    value = float(line.split()[-1])
                    stats[key] = stats.get(key, 0) + value
                except ValueError:
                    pass
    return stats


def run_benchmark(base_url: str, model: str, runs: int) -> list[RequestResult]:
    client = OpenAI(base_url=f"{base_url.rstrip('/')}/v1", api_key="unused")
    results = []

    for scenario in SCENARIOS:
        run_results = []
        print(f"\nScenario: {scenario['name']}")
        for i in range(runs):
            print(f"  run {i+1}/{runs} ...", end=" ", flush=True)
            r = stream_request(client, model, scenario["messages"], scenario["max_tokens"])
            if r.error:
                print(f"ERROR: {r.error}")
            else:
                r.scenario = scenario["name"]
                run_results.append(r)
                print(f"TTFT={r.ttft_s:.2f}s  total={r.total_s:.2f}s  {r.tokens_per_s:.0f} tok/s  ${r.gpu_cost_usd:.5f}")

        if run_results:
            # aggregate: use median for latency, sum tokens from last run
            agg = RequestResult(
                scenario=scenario["name"],
                input_tokens=run_results[-1].input_tokens,
                output_tokens=run_results[-1].output_tokens,
                ttft_s=median(r.ttft_s for r in run_results),
                total_s=median(r.total_s for r in run_results),
                tokens_per_s=median(r.tokens_per_s for r in run_results),
                gpu_cost_usd=median(r.gpu_cost_usd for r in run_results),
            )
            results.append(agg)

    return results


def print_table(results: list[RequestResult], base_url: str) -> None:
    print("\n\n## Cost + Latency Table — Modal L40S (Gemma 4 26B FP8 TurboQuant)")
    print(f"_Pricing: L40S @ $1.922/hr = $0.000534/s · Base URL: {base_url}_\n")

    header = (
        "| Scenario | Input Tok | Output Tok | TTFT (s) | Latency (s) | Tok/s | GPU $/req |"
    )
    sep = "|---|---|---|---|---|---|---|"
    print(header)
    print(sep)
    for r in results:
        print(
            f"| {r.scenario} "
            f"| {r.input_tokens:,} "
            f"| {r.output_tokens:,} "
            f"| {r.ttft_s:.2f} "
            f"| {r.total_s:.2f} "
            f"| {r.tokens_per_s:.0f} "
            f"| ${r.gpu_cost_usd:.5f} |"
        )

    # cost context
    if results:
        print("\n### Cost context")
        avg_cost = mean(r.gpu_cost_usd for r in results)
        print(f"- Average GPU cost per request: **${avg_cost:.5f}**")
        print(f"- Cost for 1,000 requests/day (avg): **${avg_cost * 1000:.2f}/day**")
        print(f"- Cold-start penalty: first request after idle adds ~60–120s container spin-up")
        print(f"  (Modal `scaledown_window=20min` keeps container warm between sessions)")
        print(f"- With `@modal.concurrent(max_inputs=10)`, batched requests amortise GPU time")
        print(f"  → effective per-request cost drops proportionally at high concurrency")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark Modal OSS deployment")
    parser.add_argument("--mode", choices=["turbo", "standard"], default="turbo")
    parser.add_argument("--runs", type=int, default=2, help="Runs per scenario (use median)")
    args = parser.parse_args()

    if args.mode == "turbo":
        base_url = os.getenv("MODAL_TURBO_BASE_URL", "")
    else:
        base_url = os.getenv("MODAL_STANDARD_BASE_URL", "")

    model = os.getenv("MODAL_MODEL", "google/gemma-4-26B-A4B-it")

    if not base_url:
        sys.exit(
            f"ERROR: MODAL_{'TURBO' if args.mode == 'turbo' else 'STANDARD'}_BASE_URL not set. "
            "Add it to your .env file."
        )

    print(f"Benchmarking {args.mode} deployment at {base_url}")
    print(f"Model: {model}  |  Runs per scenario: {args.runs}")
    print(f"L40S pricing: $1.922/hr = ${L40S_COST_PER_SECOND:.6f}/s\n")

    # pull vLLM server-side metrics snapshot before benchmark
    print("Fetching vLLM /metrics snapshot (pre-benchmark)...")
    pre_metrics = fetch_vllm_metrics(base_url)

    results = run_benchmark(base_url, model, args.runs)

    # pull vLLM server-side metrics snapshot after benchmark
    print("\nFetching vLLM /metrics snapshot (post-benchmark)...")
    post_metrics = fetch_vllm_metrics(base_url)

    # compute server-side deltas for sanity check
    if pre_metrics and post_metrics:
        delta_reqs = (
            post_metrics.get("vllm:e2e_request_latency_seconds_count", 0)
            - pre_metrics.get("vllm:e2e_request_latency_seconds_count", 0)
        )
        delta_gen_toks = (
            post_metrics.get("vllm:num_generation_tokens_total", 0)
            - pre_metrics.get("vllm:num_generation_tokens_total", 0)
        )
        delta_lat_sum = (
            post_metrics.get("vllm:e2e_request_latency_seconds_sum", 0)
            - pre_metrics.get("vllm:e2e_request_latency_seconds_sum", 0)
        )
        delta_ttft_sum = (
            post_metrics.get("vllm:time_to_first_token_seconds_sum", 0)
            - pre_metrics.get("vllm:time_to_first_token_seconds_sum", 0)
        )
        if delta_reqs > 0:
            print(f"\n[vLLM server-side delta over benchmark]")
            print(f"  Requests processed : {delta_reqs:.0f}")
            print(f"  Avg e2e latency    : {delta_lat_sum / delta_reqs:.2f}s")
            print(f"  Avg TTFT           : {delta_ttft_sum / delta_reqs:.2f}s")
            print(f"  Generation tokens  : {delta_gen_toks:.0f}")

    print_table(results, base_url)


if __name__ == "__main__":
    main()
