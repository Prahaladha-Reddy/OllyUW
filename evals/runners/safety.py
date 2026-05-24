from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from evals.common import DATASET_DIR, REPORT_DIR, add_common_args, load_jsonl, model_list, pct
from evals.harness import call_model
from evals.judges.safety_refusal import classify_refusal

AGENT_PARENT = Path(__file__).resolve().parents[2] / "e2b-template"
if str(AGENT_PARENT) not in sys.path:
    sys.path.insert(0, str(AGENT_PARENT))

from agent.safety.injection_scanner import sanitize_for_model  # noqa: E402
from agent.safety.output_validator import validate as validate_output  # noqa: E402


async def run_safety(models: list[str], limit: int = 0) -> dict[str, dict[str, Any]]:
    jailbreak_rows = load_jsonl(DATASET_DIR / "safety_jailbreaks.jsonl")
    inject_rows = load_jsonl(DATASET_DIR / "safety_indirect_inject.jsonl")
    benign_rows = load_jsonl(DATASET_DIR / "safety_benign.jsonl")
    if limit:
        jailbreak_rows = jailbreak_rows[:limit]
        inject_rows = inject_rows[:limit]
        benign_rows = benign_rows[:limit]

    results: dict[str, dict[str, Any]] = {}
    for model in models:
        jailbreak_pass = 0
        agentdojo_total = 0
        agentdojo_success = 0
        over_refusals = 0
        validator_caught = 0
        validator_total = 0
        failures: list[dict[str, Any]] = []

        for row in jailbreak_rows:
            response = await call_model(model, {}, row.get("prompt", ""))
            refusal = classify_refusal(response.get("response", ""), should_refuse=bool(row.get("should_refuse", True)))
            validation = validate_output(response.get("response", ""), source_texts={})
            validator_total += 1
            if not validation.is_valid:
                validator_caught += 1
            if refusal.passed:
                jailbreak_pass += 1
            else:
                failures.append({"id": row.get("id"), "suite": "jailbreak", "response": response.get("response", ""), "rationale": refusal.rationale})

        for row in inject_rows:
            docs, scanner_flagged = _sanitize_documents(row.get("documents", {}))
            response = await call_model(model, docs, row.get("question", ""))
            text = response.get("response", "")
            refusal = classify_refusal(text, should_refuse=bool(row.get("should_refuse", True)))
            validation = validate_output(text, source_texts=docs)
            validator_total += 1
            if scanner_flagged or not validation.is_valid:
                validator_caught += 1
            if row.get("benchmark") == "AgentDojo":
                agentdojo_total += 1
                if not refusal.passed:
                    agentdojo_success += 1
            if not refusal.passed:
                failures.append({"id": row.get("id"), "suite": "indirect_injection", "response": text, "rationale": refusal.rationale})

        for row in benign_rows:
            response = await call_model(model, {}, row.get("prompt", ""))
            refusal = classify_refusal(response.get("response", ""), should_refuse=False)
            if refusal.refused:
                over_refusals += 1
                failures.append({"id": row.get("id"), "suite": "over_refusal", "response": response.get("response", ""), "rationale": refusal.rationale})

        results[model] = {
            "jailbreak_refusal": pct(jailbreak_pass, len(jailbreak_rows)),
            "agentdojo_asr": pct(agentdojo_success, agentdojo_total),
            "over_refusal_rate": pct(over_refusals, len(benign_rows)),
            "validator_catch_rate": pct(validator_caught, validator_total),
            "failures": failures,
        }
        _write_failures(model, failures)

    return results


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
    results = asyncio.run(run_safety(model_list(args.models), limit=args.limit))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
