from __future__ import annotations

import argparse
import asyncio
import csv
from typing import Any

from evals.common import DATASET_DIR, REPORT_DIR, add_common_args, load_jsonl, model_list
from evals.datasets.build_seed_data import main as build_seed_data
from evals.runners.bias import run_bias
from evals.runners.hallucination import run_hallucination
from evals.runners.safety import run_safety


async def run_all(models: list[str], limit: int = 0) -> dict[str, dict[str, Any]]:
    _ensure_datasets()
    hallucination, bias, safety = await asyncio.gather(
        run_hallucination(models, limit=limit),
        run_bias(models, limit=limit),
        run_safety(models, limit=limit),
    )
    combined: dict[str, dict[str, Any]] = {}
    for model in models:
        combined[model] = {
            "hallucination": hallucination.get(model, {}),
            "bias": bias.get(model, {}),
            "safety": safety.get(model, {}),
        }
    _write_report(combined, models)
    _write_csv(combined, models)
    return combined


def _ensure_datasets() -> None:
    required = [
        DATASET_DIR / "hallucination_factual.jsonl",
        DATASET_DIR / "bias_bbq.jsonl",
        DATASET_DIR / "bias_demographic_perm.jsonl",
        DATASET_DIR / "safety_jailbreaks.jsonl",
        DATASET_DIR / "safety_benign.jsonl",
        DATASET_DIR / "safety_indirect_inject.jsonl",
        DATASET_DIR / "source_manifest.json",
    ]
    if not all(path.exists() for path in required):
        build_seed_data()


def _write_report(results: dict[str, dict[str, Any]], models: list[str]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / "eval_report.md"
    sizes = _dataset_sizes()
    path.write_text(_render_report(results, models, sizes), encoding="utf-8")


def _dataset_sizes() -> dict[str, int]:
    return {
        "hallucination_factual": len(load_jsonl(DATASET_DIR / "hallucination_factual.jsonl")),
        "bias_bbq": len(load_jsonl(DATASET_DIR / "bias_bbq.jsonl")),
        "bias_demographic_perm": len(load_jsonl(DATASET_DIR / "bias_demographic_perm.jsonl")),
        "safety_jailbreaks": len(load_jsonl(DATASET_DIR / "safety_jailbreaks.jsonl")),
        "safety_benign": len(load_jsonl(DATASET_DIR / "safety_benign.jsonl")),
        "safety_indirect_inject": len(load_jsonl(DATASET_DIR / "safety_indirect_inject.jsonl")),
    }


def _render_report(results: dict[str, dict[str, Any]], models: list[str], sizes: dict[str, int]) -> str:
    lines = [
        "# OllyUW Evaluation Report",
        "",
        "## Methodology",
        "",
        "The suite evaluates the same three risks required by the assignment: hallucination, bias, and content safety.",
        "Citation grounding uses deterministic quote substring checks first. DeepSeek is the configured LLM judge for optional borderline adjudication and refusal classification, keeping the eval single-provider.",
        "All bundled rows are pulled from public benchmark sources by evals.datasets.build_seed_data; no synthetic underwriting packages are generated.",
        "",
        "Dataset sizes used in this run:",
        f"- HaluEval QA rows: {sizes['hallucination_factual']}",
        f"- BBQ rows: {sizes['bias_bbq']}",
        f"- Public underwriting counterfactual rows: {sizes['bias_demographic_perm']} (N/A if no real public set is available)",
        f"- JailbreakBench harmful rows: {sizes['safety_jailbreaks']}",
        f"- JailbreakBench benign rows: {sizes['safety_benign']}",
        f"- AgentDojo indirect-injection rows: {sizes['safety_indirect_inject']}",
        "",
        "Reproduce with:",
        "",
        "```powershell",
        "$env:PYTHONPATH = (Get-Location).Path",
        "uv run --project backend python -m evals.runners.all --models modal,deepseek",
        "```",
        "",
        "For a local smoke test without model API calls:",
        "",
        "```powershell",
        "$env:PYTHONPATH = (Get-Location).Path",
        "uv run --project backend python -m evals.runners.all --models mock",
        "```",
        "",
        "## Results",
        "",
        "### Hallucination (citation grounding + factual accuracy)",
        "| Model | HaluEval-QA acc | Citation precision | Citation recall | Score MSE |",
        "|---|---:|---:|---:|---:|",
    ]
    for model in models:
        h = results[model]["hallucination"]
        lines.append(
            f"| {model} | {_fmt_pct(h.get('halu_eval_qa_acc'))} | {_fmt_pct(h.get('citation_precision'))} | "
            f"{_fmt_pct(h.get('citation_recall'))} | {_fmt_number_or_na(h.get('score_mse'))} |"
        )

    lines.extend(
        [
            "",
            "### Bias (BBQ + public counterfactual variance if available)",
            "| Model | BBQ accuracy | Demographic score variance | Pass (<=2pt)? |",
            "|---|---:|---:|:---:|",
        ]
    )
    for model in models:
        b = results[model]["bias"]
        variance = _fmt_number_or_na(b.get("demographic_score_variance"))
        delta = _fmt_number_or_na(b.get("demographic_score_max_delta"))
        passed = "N/A" if b.get("pass_le_2pt") is None else ("Y" if b.get("pass_le_2pt") else "N")
        lines.append(
            f"| {model} | {_fmt_pct(b.get('bbq_accuracy'))} | {variance} "
            f"(avg max delta {delta}) | {passed} |"
        )

    lines.extend(
        [
            "",
            "### Content Safety (jailbreak + indirect injection + over-refusal)",
            "| Model | JailbreakBench refusal | AgentDojo ASR | Over-refusal rate | Validator catch rate |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for model in models:
        s = results[model]["safety"]
        lines.append(
            f"| {model} | {_fmt_pct(s.get('jailbreak_refusal'))} | {_fmt_pct(s.get('agentdojo_asr'))} | "
            f"{_fmt_pct(s.get('over_refusal_rate'))} | {_fmt_pct(s.get('validator_catch_rate'))} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Use the hallucination table to decide whether the open-source path is accurate enough for extraction and scoring. Use the bias and safety tables to decide whether the frontier model is still needed for final memo reasoning.",
            "The recommended production pattern remains hybrid: OSS for low-cost extraction and repeatable scoring assistance, frontier/DeepSeek for final reasoning, safety adjudication, and eval judging when deterministic checks are borderline.",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_csv(results: dict[str, dict[str, Any]], models: list[str]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / "comparison_table.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "model",
                "halu_eval_qa_acc",
                "citation_precision",
                "citation_recall",
                "score_mse",
                "bbq_accuracy",
                "demographic_score_variance",
                "demographic_score_max_delta",
                "bias_pass_le_2pt",
                "jailbreak_refusal",
                "agentdojo_asr",
                "over_refusal_rate",
                "validator_catch_rate",
            ],
        )
        writer.writeheader()
        for model in models:
            h = results[model]["hallucination"]
            b = results[model]["bias"]
            s = results[model]["safety"]
            writer.writerow(
                {
                    "model": model,
                    "halu_eval_qa_acc": h.get("halu_eval_qa_acc", 0),
                    "citation_precision": h.get("citation_precision", 0),
                    "citation_recall": h.get("citation_recall", 0),
                    "score_mse": h.get("score_mse", 0),
                    "bbq_accuracy": b.get("bbq_accuracy", 0),
                    "demographic_score_variance": b.get("demographic_score_variance", 0),
                    "demographic_score_max_delta": b.get("demographic_score_max_delta", 0),
                    "bias_pass_le_2pt": b.get("pass_le_2pt", False),
                    "jailbreak_refusal": s.get("jailbreak_refusal", 0),
                    "agentdojo_asr": s.get("agentdojo_asr", 0),
                    "over_refusal_rate": s.get("over_refusal_rate", 0),
                    "validator_catch_rate": s.get("validator_catch_rate", 0),
                }
            )


def _fmt_pct(value: Any) -> str:
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return "0.0%"


def _fmt_number_or_na(value: Any) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "N/A"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all OllyUW eval suites and write reports.")
    add_common_args(parser)
    args = parser.parse_args()
    models = model_list(args.models)
    results = asyncio.run(run_all(models, limit=args.limit))
    print(f"Wrote {REPORT_DIR / 'eval_report.md'}")
    print(f"Wrote {REPORT_DIR / 'comparison_table.csv'}")
    for model in models:
        print(f"{model}: {results[model]}")


if __name__ == "__main__":
    main()
