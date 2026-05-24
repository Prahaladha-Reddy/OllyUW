from __future__ import annotations

import argparse
import asyncio
import json
from collections import defaultdict
from typing import Any

from evals.common import DATASET_DIR, REPORT_DIR, add_common_args, load_jsonl, mean, model_list, parse_choice, parse_overall_score, pct
from evals.harness import call_model
from evals.judges.bias_variance import score_variance


async def run_bias(models: list[str], limit: int = 0) -> dict[str, dict[str, Any]]:
    bbq_rows = load_jsonl(DATASET_DIR / "bias_bbq.jsonl")
    perm_rows = load_jsonl(DATASET_DIR / "bias_demographic_perm.jsonl")
    if limit:
        bbq_rows = bbq_rows[:limit]
        perm_rows = perm_rows[: max(limit, 4)]

    results: dict[str, dict[str, Any]] = {}
    for model in models:
        bbq_correct = 0
        failures: list[dict[str, Any]] = []

        for row in bbq_rows:
            choices = row.get("choices", [])
            prompt = (
                f"{row.get('context', '')}\n\n"
                f"{row.get('question', '')}\n"
                + "\n".join(f"{chr(ord('A') + idx)}. {choice}" for idx, choice in enumerate(choices))
                + "\nAnswer with only A, B, C, or D plus one sentence."
            )
            response = await call_model(model, {"bbq_context.md": row.get("context", "")}, prompt)
            choice = parse_choice(response.get("response", ""), choices)
            if choice == row.get("correct_label"):
                bbq_correct += 1
            else:
                failures.append(
                    {
                        "id": row.get("id"),
                        "suite": "bbq",
                        "choice": choice,
                        "expected": row.get("correct_label"),
                        "response": response.get("response", ""),
                    }
                )

        scores_by_base: dict[str, list[float]] = defaultdict(list)
        for row in perm_rows:
            response = await call_model(model, row.get("documents", {}), row.get("question", ""))
            score = parse_overall_score(response.get("response", ""))
            if score is None:
                failures.append({"id": row.get("id"), "suite": "demographic_perm", "response": response.get("response", "")})
                continue
            scores_by_base[row["base_id"]].append(score)

        variance_results = [score_variance(scores) for scores in scores_by_base.values() if scores]
        avg_std = mean([item.std_dev for item in variance_results]) if variance_results else None
        avg_delta = mean([item.max_delta for item in variance_results]) if variance_results else None
        passed = all(item.passed for item in variance_results) if variance_results else None

        results[model] = {
            "bbq_accuracy": pct(bbq_correct, len(bbq_rows)),
            "demographic_score_variance": avg_std,
            "demographic_score_max_delta": avg_delta,
            "pass_le_2pt": passed,
            "demographic_score_variance_note": (
                "" if variance_results else
                "N/A: no public real underwriting counterfactual profile set is bundled"
            ),
            "failures": failures,
        }
        _write_failures(model, failures)

    return results


def _write_failures(model: str, failures: list[dict[str, Any]]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"bias_failures_{model}.json"
    path.write_text(json.dumps(failures, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OllyUW bias evals.")
    add_common_args(parser)
    args = parser.parse_args()
    results = asyncio.run(run_bias(model_list(args.models), limit=args.limit))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
