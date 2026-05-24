from __future__ import annotations

import argparse
import asyncio
import json
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
from evals.harness import QA_SYSTEM_PROMPT, call_model
from evals.judges.citation_grounding import citation_recall


def _percentile(values: list[float], p: int) -> float | None:
    if not values:
        return None
    s = sorted(values)
    return s[min(len(s) - 1, int(len(s) * p / 100))]


async def run_hallucination(
    models: list[str],
    limit: int = 0,
    caller: EvalCaller = call_model,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> dict[str, dict[str, Any]]:
    rows = load_jsonl(DATASET_DIR / "hallucination_factual.jsonl")
    if limit:
        rows = rows[:limit]

    async def run_model(model: str) -> tuple[str, dict[str, Any]]:
        qa_correct = 0
        qa_hallucinated = 0
        recall_values: list[float] = []
        latencies: list[float] = []
        total_input_tokens = 0
        total_output_tokens = 0
        failures: list[dict[str, Any]] = []

        async def run_row(row: dict[str, Any]) -> dict[str, Any]:
            # No documents sent — pure parametric knowledge test as per eval design.
            response = await caller(model, {}, row.get("question", ""), QA_SYSTEM_PROMPT)
            return {"row": row, "response": response}

        row_results = await gather_limited(rows, concurrency, run_row)

        for item in row_results:
            row = item["row"]
            response = item["response"]
            text = response.get("response", "")
            expected = str(row.get("expected_answer", ""))
            hallucinated = str(row.get("hallucinated_answer", ""))

            if response.get("error"):
                failures.append({"id": row.get("id"), "suite": "qa", "error": response.get("error")})
                continue

            if response.get("latency_s"):
                latencies.append(response["latency_s"])
            total_input_tokens += response.get("input_tokens") or 0
            total_output_tokens += response.get("output_tokens") or 0

            if expected and expected.lower() in text.lower():
                qa_correct += 1
            else:
                failures.append({
                    "id": row.get("id"),
                    "suite": "qa",
                    "response": text[:300],
                    "expected": expected,
                })

            if hallucinated and hallucinated.lower() in text.lower():
                qa_hallucinated += 1

            recall_values.append(citation_recall(text, row.get("required_quotes", [])))

        result = {
            "halu_eval_qa_acc": pct(qa_correct, len(rows)),
            "hallucination_rate": pct(qa_hallucinated, len(rows)),
            "citation_precision": None,
            "citation_recall": pct(sum(recall_values), len(recall_values)) if recall_values else None,
            "citation_precision_note": "N/A: no source documents sent (parametric-knowledge eval mode)",
            "score_mse": None,
            "score_mse_note": "N/A: HaluEval rows do not contain underwriting risk-score ground truth",
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
    path = REPORT_DIR / f"hallucination_failures_{model}.json"
    path.write_text(json.dumps(failures, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OllyUW hallucination/citation evals.")
    add_common_args(parser)
    args = parser.parse_args()
    results = asyncio.run(
        run_hallucination(
            model_list(args.models),
            limit=args.limit,
            concurrency=args.concurrency,
        )
    )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
