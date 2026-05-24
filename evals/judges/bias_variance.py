from __future__ import annotations

from dataclasses import dataclass

from evals.common import stddev


@dataclass(frozen=True)
class VarianceResult:
    std_dev: float
    max_delta: float
    passed: bool


def score_variance(scores: list[float], tolerance_points: float = 2.0) -> VarianceResult:
    if not scores:
        return VarianceResult(std_dev=0.0, max_delta=0.0, passed=True)
    max_delta = max(scores) - min(scores)
    return VarianceResult(
        std_dev=stddev(scores),
        max_delta=max_delta,
        passed=max_delta <= tolerance_points,
    )
