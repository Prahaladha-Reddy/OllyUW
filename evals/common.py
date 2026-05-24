from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
from pathlib import Path
from typing import Any, Awaitable, Callable

ROOT = Path(__file__).resolve().parent
DATASET_DIR = ROOT / "datasets"
REPORT_DIR = ROOT / "reports"
DEFAULT_MODELS = ("modal", "deepseek")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL in {path}:{line_no}: {exc}") from exc
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")


def read_submission(case_dir: Path) -> dict[str, str]:
    docs: dict[str, str] = {}
    for path in sorted(case_dir.rglob("*")):
        if path.name == "truth.json" or not path.is_file():
            continue
        try:
            docs[path.relative_to(case_dir).as_posix()] = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
    return docs


def load_truth(case_dir: Path) -> dict[str, Any]:
    truth_path = case_dir / "truth.json"
    if not truth_path.exists():
        return {}
    return json.loads(truth_path.read_text(encoding="utf-8"))


def synthetic_cases() -> list[Path]:
    root = DATASET_DIR / "synthetic_submissions"
    if not root.exists():
        return []
    return sorted(path for path in root.iterdir() if path.is_dir())


def parse_overall_score(response: str) -> float | None:
    patterns = [
        r"OVERALL\s+SCORE\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*/\s*100",
        r"overall\s+risk\s+score\s*(?:is|=|:)\s*([0-9]+(?:\.[0-9]+)?)",
        r"\bscore\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)\s*/\s*100",
    ]
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def parse_choice(response: str, choices: list[str]) -> str | None:
    text = response.strip()
    first = re.match(r"^\s*([A-D])\b", text, re.IGNORECASE)
    if first:
        return first.group(1).upper()
    for idx, choice in enumerate(choices):
        label = chr(ord("A") + idx)
        if re.search(rf"\b{re.escape(choice)}\b", text, re.IGNORECASE):
            return label
    return None


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def mse(predicted: list[float], expected: list[float]) -> float:
    pairs = list(zip(predicted, expected, strict=False))
    if not pairs:
        return 0.0
    return sum((a - b) ** 2 for a, b in pairs) / len(pairs)


def stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = mean(values)
    return math.sqrt(sum((value - avg) ** 2 for value in values) / len(values))


def pct(numerator: float, denominator: float) -> float:
    return (numerator / denominator * 100.0) if denominator else 0.0


def model_list(value: str | None) -> list[str]:
    if not value:
        return list(DEFAULT_MODELS)
    return [part.strip() for part in value.split(",") if part.strip()]


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--models",
        default=",".join(DEFAULT_MODELS),
        help="Comma-separated model ids: modal, deepseek, or mock.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional per-suite row limit for smoke runs.",
    )


async def gather_limited(
    items: list[Any],
    limit: int,
    worker: Callable[[Any], Awaitable[Any]],
) -> list[Any]:
    semaphore = asyncio.Semaphore(limit)

    async def run_one(item: Any) -> Any:
        async with semaphore:
            return await worker(item)

    return await asyncio.gather(*(run_one(item) for item in items))
