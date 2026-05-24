from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from evals.common import (
    DATASET_DIR,
    DEFAULT_CONCURRENCY,
    EvalCaller,
    REPORT_DIR,
    add_common_args,
    gather_limited,
    load_jsonl,
    model_list,
    pct,
)
from evals.harness import EVAL_SYSTEM_PROMPT, SAFETY_SYSTEM_PROMPT, call_model
from evals.judges.safety_refusal import classify_refusal


def _percentile(values: list[float], p: int) -> float | None:
    if not values:
        return None
    s = sorted(values)
    return s[min(len(s) - 1, int(len(s) * p / 100))]

# Pull the layer-3 validator from the agent package without importing all of e2b-template.
_AGENT_PARENT = Path(__file__).resolve().parents[2] / "e2b-template"
if str(_AGENT_PARENT) not in sys.path:
    sys.path.insert(0, str(_AGENT_PARENT))

try:
    from agent.safety.injection_scanner import sanitize_for_model
    from agent.safety.output_validator import validate as validate_output
    _VALIDATOR_AVAILABLE = True
except ImportError:
    _VALIDATOR_AVAILABLE = False

    def sanitize_for_model(text: str, source: str = "") -> tuple[str, Any]:  # type: ignore[misc]
        class _R:
            flagged = False
        return text, _R()

    def validate_output(output: str, **_: Any) -> Any:  # type: ignore[misc]
        class _R:
            is_valid = True
        return _R()


async def run_safety(
    models: list[str],
    limit: int = 0,
    caller: EvalCaller = call_model,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> dict[str, dict[str, Any]]:
    jailbreak_rows = load_jsonl(DATASET_DIR / "safety_jailbreaks.jsonl")
    inject_rows = load_jsonl(DATASET_DIR / "safety_indirect_inject.jsonl")
    benign_rows = load_jsonl(DATASET_DIR / "safety_benign.jsonl")
    if limit:
        jailbreak_rows = jailbreak_rows[:limit]
        inject_rows = inject_rows[:limit]
        benign_rows = benign_rows[:limit]

    async def run_model(model: str) -> tuple[str, dict[str, Any]]:
        jailbreak_pass = 0
        agentdojo_total = 0
        agentdojo_success = 0
        over_refusals = 0
        validator_caught = 0
        validator_total = 0
        latencies: list[float] = []
        total_input_tokens = 0
        total_output_tokens = 0
        failures: list[dict[str, Any]] = []

        # ── Jailbreak refusal ────────────────────────────────────────────────
        async def run_jailbreak(row: dict[str, Any]) -> dict[str, Any]:
            # No documents — jailbreak prompt is sent directly to OllyUW persona.
            response = await caller(model, {}, row.get("prompt", ""), SAFETY_SYSTEM_PROMPT)
            return {"row": row, "response": response}

        for item in await gather_limited(jailbreak_rows, concurrency, run_jailbreak):
            row = item["row"]
            response = item["response"]
            if response.get("error"):
                failures.append({"id": row.get("id"), "suite": "jailbreak", "error": response.get("error")})
                continue
            if response.get("latency_s"):
                latencies.append(response["latency_s"])
            total_input_tokens += response.get("input_tokens") or 0
            total_output_tokens += response.get("output_tokens") or 0
            text = response.get("response", "")
            refusal = classify_refusal(text, should_refuse=bool(row.get("should_refuse", True)))
            if _VALIDATOR_AVAILABLE:
                validation = validate_output(text, source_texts={})
                validator_total += 1
                if not validation.is_valid:
                    validator_caught += 1
            if refusal.passed:
                jailbreak_pass += 1
            else:
                failures.append({
                    "id": row.get("id"),
                    "suite": "jailbreak",
                    "response": text[:300],
                    "rationale": refusal.rationale,
                })

        # ── Indirect injection ───────────────────────────────────────────────
        async def run_injection(row: dict[str, Any]) -> dict[str, Any]:
            docs, scanner_flagged = _sanitize_documents(row.get("documents", {}))
            response = await caller(model, docs, row.get("question", ""), EVAL_SYSTEM_PROMPT)
            return {"row": row, "docs": docs, "scanner_flagged": scanner_flagged, "response": response}

        for item in await gather_limited(inject_rows, concurrency, run_injection):
            row = item["row"]
            docs = item["docs"]
            scanner_flagged = item["scanner_flagged"]
            response = item["response"]
            if response.get("error"):
                failures.append({"id": row.get("id"), "suite": "indirect_injection", "error": response.get("error")})
                continue
            if response.get("latency_s"):
                latencies.append(response["latency_s"])
            total_input_tokens += response.get("input_tokens") or 0
            total_output_tokens += response.get("output_tokens") or 0
            text = response.get("response", "")
            refusal = classify_refusal(text, should_refuse=bool(row.get("should_refuse", True)))
            if _VALIDATOR_AVAILABLE:
                validation = validate_output(text, source_texts=docs)
                validator_total += 1
                if scanner_flagged or not validation.is_valid:
                    validator_caught += 1
            if row.get("benchmark") == "AgentDojo":
                agentdojo_total += 1
                if not refusal.passed:
                    agentdojo_success += 1
            if not refusal.passed:
                failures.append({
                    "id": row.get("id"),
                    "suite": "indirect_injection",
                    "response": text[:300],
                    "rationale": refusal.rationale,
                })

        # ── Over-refusal (benign prompts that should be answered) ────────────
        async def run_benign(row: dict[str, Any]) -> dict[str, Any]:
            response = await caller(model, {}, row.get("prompt", ""), SAFETY_SYSTEM_PROMPT)
            return {"row": row, "response": response}

        for item in await gather_limited(benign_rows, concurrency, run_benign):
            row = item["row"]
            response = item["response"]
            if response.get("error"):
                failures.append({"id": row.get("id"), "suite": "over_refusal", "error": response.get("error")})
                continue
            total_input_tokens += response.get("input_tokens") or 0
            total_output_tokens += response.get("output_tokens") or 0
            text = response.get("response", "")
            refusal = classify_refusal(text, should_refuse=False)
            if refusal.refused:
                over_refusals += 1
                failures.append({
                    "id": row.get("id"),
                    "suite": "over_refusal",
                    "response": text[:300],
                    "rationale": refusal.rationale,
                })

        result = {
            "jailbreak_refusal": pct(jailbreak_pass, len(jailbreak_rows)),
            "agentdojo_asr": pct(agentdojo_success, agentdojo_total),
            "over_refusal_rate": pct(over_refusals, len(benign_rows)),
            "validator_catch_rate": pct(validator_caught, validator_total) if validator_total else None,
            "validator_available": _VALIDATOR_AVAILABLE,
            "p50_latency_s": _percentile(latencies, 50),
            "p90_latency_s": _percentile(latencies, 90),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "failures": failures,
        }
        _write_failures(model, failures)
        return model, result

    pairs = await asyncio.gather(*(run_model(model) for model in models))
    return dict(pairs)


def _sanitize_documents(documents: dict[str, str]) -> tuple[dict[str, str], bool]:
    sanitized: dict[str, str] = {}
    flagged = False
    for filename, content in documents.items():
        safe_content, result = sanitize_for_model(content, source=filename)
        sanitized[filename] = safe_content
        flagged = flagged or result.flagged
    return sanitized, flagged


def _write_failures(model: str, failures: list[dict[str, Any]]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"safety_failures_{model}.json"
    path.write_text(json.dumps(failures, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OllyUW content-safety evals.")
    add_common_args(parser)
    args = parser.parse_args()
    results = asyncio.run(
        run_safety(
            model_list(args.models),
            limit=args.limit,
            concurrency=args.concurrency,
        )
    )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
