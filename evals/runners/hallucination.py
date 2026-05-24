from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from evals.common import (
    DATASET_DIR,
    REPORT_DIR,
    add_common_args,
    load_jsonl,
    model_list,
    pct,
)
from evals.harness import call_model
from evals.judges.citation_grounding import check_quote_substrings, citation_recall


async def run_hallucination(models: list[str], limit: int = 0) -> dict[str, dict[str, Any]]:
    rows = load_jsonl(DATASET_DIR / "hallucination_factual.jsonl")
    if limit:
        rows = rows[:limit]

    results: dict[str, dict[str, Any]] = {}
    for model in models:
        qa_correct = 0
        citation_total = 0
        citation_accurate = 0
        recall_values: list[float] = []
        failures: list[dict[str, Any]] = []

        for row in rows:
            response = await call_model(model, row.get("documents", {}), row.get("question", ""))
            text = response.get("response", "")
            expected = str(row.get("expected_answer", ""))
            if expected and expected.lower() in text.lower():
                qa_correct += 1
            else:
                failures.append({"id": row.get("id"), "suite": "qa", "response": text, "expected": expected})

            citation_result = check_quote_substrings(text, row.get("documents", {}))
            citation_total += citation_result.total
            citation_accurate += citation_result.accurate
            recall_values.append(citation_recall(text, row.get("required_quotes", [])))

        results[model] = {
            "halu_eval_qa_acc": pct(qa_correct, len(rows)),
            "citation_precision": pct(citation_accurate, citation_total),
            "citation_recall": pct(sum(recall_values), len(recall_values)),
            "score_mse": None,
            "score_mse_note": "N/A: public HaluEval rows do not contain underwriting risk-score ground truth",
            "failures": failures,
        }
        _write_failures(model, failures)

    return results


def _write_failures(model: str, failures: list[dict[str, Any]]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"hallucination_failures_{model}.json"
    path.write_text(json.dumps(failures, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OllyUW hallucination/citation evals.")
    add_common_args(parser)
    args = parser.parse_args()
    results = asyncio.run(run_hallucination(model_list(args.models), limit=args.limit))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
