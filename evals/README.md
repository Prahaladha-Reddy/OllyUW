# OllyUW Eval Framework

This directory ships beside `e2b-template/` and evaluates the two model paths on the assignment rubric:

- hallucination: HaluEval-QA factual QA and citation precision/recall
- bias: BBQ ambiguous-question accuracy, plus counterfactual score variance only if a real public profile set is supplied
- content safety: jailbreak refusal, indirect injection resistance, validator catch rate, and over-refusal

## Reproduce

From the repository root:

```powershell
$env:PYTHONPATH = (Get-Location).Path
uv run --project backend python -m evals.datasets.build_seed_data
uv run --project backend python -m evals.runners.all --models modal,deepseek
```

For a no-API smoke test:

```powershell
$env:PYTHONPATH = (Get-Location).Path
uv run --project backend python -m evals.runners.all --models mock
```

The report generator writes:

- `evals/reports/eval_report.md`
- `evals/reports/comparison_table.csv`
- `evals/reports/*_failures_<model>.json`

`evals/reports/` is gitignored because reports are run artifacts.

## Public Data Sources

`evals.datasets.build_seed_data` downloads real public benchmark rows and writes source metadata into `evals/datasets/source_manifest.json`.

- `hallucination_factual.jsonl`: 50 HaluEval-QA rows from `shunk031/HaluEval`
- `bias_bbq.jsonl`: 50 BBQ rows from `HiTZ/bbq`, balanced across age, gender identity, nationality, and SES
- `bias_demographic_perm.jsonl`: empty by design; there is no bundled real public underwriting counterfactual profile set
- `safety_jailbreaks.jsonl`: 50 harmful behavior rows from `JailbreakBench/JBB-Behaviors`
- `safety_benign.jsonl`: 50 benign behavior rows from `JailbreakBench/JBB-Behaviors` for over-refusal
- `safety_indirect_inject.jsonl`: all available AgentDojo default-suite injection task goals from `ethz-spylab/agentdojo`, capped at 50

No synthetic underwriting package directory is generated. If a real public underwriting counterfactual dataset becomes available, add it to `bias_demographic_perm.jsonl` using the existing schema and the variance judge will pick it up.

## Judges

`judges/citation_grounding.py` performs deterministic quote substring checks. This is the primary grounding judge.

`judges/bias_variance.py` computes pure score variance across demographic permutations when such rows are present. A profile passes when max score delta is `<= 2` points.

`judges/safety_refusal.py` is a deterministic refusal classifier for smoke runs. DeepSeek is the intended LLM-as-judge for borderline safety/factuality cases when API-backed judging is enabled later.
