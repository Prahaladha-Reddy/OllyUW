from __future__ import annotations

import argparse
import asyncio
import json
from collections import defaultdict
from typing import Any

from evals.common import (
    DATASET_DIR,
    DEFAULT_CONCURRENCY,
    EvalCaller,
    REPORT_DIR,
    add_common_args,
    gather_limited,
    load_jsonl,
    mean,
    model_list,
    parse_choice,
    parse_overall_score,
    pct,
)
from evals.harness import BBQ_SYSTEM_PROMPT, EVAL_SYSTEM_PROMPT, call_model
from evals.judges.bias_variance import score_variance


def _percentile(values: list[float], p: int) -> float | None:
    if not values:
        return None
    s = sorted(values)
    return s[min(len(s) - 1, int(len(s) * p / 100))]


async def run_bias(
    models: list[str],
    limit: int = 0,
    caller: EvalCaller = call_model,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> dict[str, dict[str, Any]]:
    bbq_rows = load_jsonl(DATASET_DIR / "bias_bbq.jsonl")
    perm_rows = load_jsonl(DATASET_DIR / "bias_demographic_perm.jsonl")
    if limit:
        bbq_rows = bbq_rows[:limit]
        perm_rows = perm_rows[: max(limit, 4)]

    async def run_model(model: str) -> tuple[str, dict[str, Any]]:
        bbq_correct = 0
        latencies: list[float] = []
        total_input_tokens = 0
        total_output_tokens = 0
        failures: list[dict[str, Any]] = []

        async def run_bbq(row: dict[str, Any]) -> dict[str, Any]:
            choices = row.get("choices", [])
            # Send context + question as plain text — no document wrapper, avoids the
            # risk-assessment system prompt confusing a multiple-choice task.
            prompt = (
                f"Context: {row.get('context', '')}\n\n"
                f"Question: {row.get('question', '')}\n"
                + "\n".join(f"{chr(ord('A') + idx)}. {choice}" for idx, choice in enumerate(choices))
                + "\nAnswer with only A, B, or C plus one sentence."
            )
            response = await caller(model, {}, prompt, BBQ_SYSTEM_PROMPT)
            return {"row": row, "choices": choices, "response": response}

        for item in await gather_limited(bbq_rows, concurrency, run_bbq):
            row = item["row"]
            choices = item["choices"]
            response = item["response"]
            if response.get("error"):
                failures.append({"id": row.get("id"), "suite": "bbq", "error": response.get("error")})
                continue
            if response.get("latency_s"):
                latencies.append(response["latency_s"])
            total_input_tokens += response.get("input_tokens") or 0
            total_output_tokens += response.get("output_tokens") or 0
            choice = parse_choice(response.get("response", ""), choices)
            if choice == row.get("correct_label"):
                bbq_correct += 1
            else:
                failures.append({
                    "id": row.get("id"),
                    "suite": "bbq",
                    "choice": choice,
                    "expected": row.get("correct_label"),
                    "response": response.get("response", "")[:200],
                })

        scores_by_base: dict[str, list[float]] = defaultdict(list)

        async def run_perm(row: dict[str, Any]) -> dict[str, Any]:
            response = await caller(model, row.get("documents", {}), row.get("question", ""), EVAL_SYSTEM_PROMPT)
            return {"row": row, "response": response}

        for item in await gather_limited(perm_rows, concurrency, run_perm):
            row = item["row"]
            response = item["response"]
            if response.get("error"):
                failures.append({"id": row.get("id"), "suite": "demographic_perm", "error": response.get("error")})
                continue
            total_input_tokens += response.get("input_tokens") or 0
            total_output_tokens += response.get("output_tokens") or 0
            score = parse_overall_score(response.get("response", ""))
            if score is None:
                failures.append({
                    "id": row.get("id"),
                    "suite": "demographic_perm",
                    "response": response.get("response", "")[:200],
                })
                continue
            scores_by_base[row["base_id"]].append(score)

        variance_results = [score_variance(scores) for scores in scores_by_base.values() if scores]
        avg_std = mean([item.std_dev for item in variance_results]) if variance_results else None
        avg_delta = mean([item.max_delta for item in variance_results]) if variance_results else None
        passed = all(item.passed for item in variance_results) if variance_results else None

        result = {
            "bbq_accuracy": pct(bbq_correct, len(bbq_rows)),
            "demographic_score_variance": avg_std,
            "demographic_score_max_delta": avg_delta,
            "pass_le_2pt": passed,
            "demographic_score_variance_note": (
                "" if variance_results
                else "N/A: bias_demographic_perm.jsonl is empty"
            ),
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


def _write_failures(model: str, failures: list[dict[str, Any]]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"bias_failures_{model}.json"
    path.write_text(json.dumps(failures, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OllyUW bias evals.")
    add_common_args(parser)
    args = parser.parse_args()
    results = asyncio.run(
        run_bias(
            model_list(args.models),
            limit=args.limit,
            concurrency=args.concurrency,
        )
    )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
