"""Steps 3-6 — run the triager over the dataset and score it.

    uv run python -m evals.run_evals --model stand-in                 # no API key needed
    uv run python -m evals.run_evals                                  # real model (TRIAGER_MODEL or openai:gpt-5.2)
    JUDGE_MODEL=anthropic:claude-sonnet-4-5 uv run python -m evals.run_evals   # + LLM judge
    uv run python -m evals.run_evals --repeat 3                       # run-to-run variance
    uv run python -m evals.run_evals --baseline stand-in              # compare against another model
    uv run python -m evals.run_evals --gate 0.8                       # exit 1 below the bar (CI)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any

from pydantic_evals import Dataset
from pydantic_evals.reporting import EvaluationReport

from evals.evaluators import all_evaluators, risk_confusion_matrix
from evals.stand_in import stand_in_model
from triager import PullRequest, triage

DATASET = Path(__file__).with_name("dataset.yaml")
MUST_PASS = ("NotFallback", "NoUnderestimate")  # any failure here fails the gate


class FallbackSpy(logging.Handler):
    """Instrumentation: catch triage()'s 'using fallback' warning for this thread's call."""

    def __init__(self) -> None:
        super().__init__()
        self.thread, self.hit = threading.get_ident(), False

    def emit(self, record: logging.LogRecord) -> None:
        if record.thread == self.thread and "using fallback" in record.getMessage():
            self.hit = True


def make_task(model: Any):
    def task(inputs: dict) -> dict[str, Any]:
        spy = FallbackSpy()
        logger = logging.getLogger("triager.triage")
        logger.addHandler(spy)
        try:
            result = triage(PullRequest.model_validate(inputs), model=model)
        finally:
            logger.removeHandler(spy)
        return {**result.model_dump(), "fallback_used": spy.hit}

    return task


def resolve(model: str | None) -> Any:
    model = model or os.environ.get("TRIAGER_MODEL", "openai:gpt-5.2")
    return stand_in_model if model == "stand-in" else model


def run(dataset: Dataset, model: str | None, name: str | None, repeat: int) -> EvaluationReport:
    return dataset.evaluate_sync(make_task(resolve(model)), name=name or model, repeat=repeat, max_concurrency=4, progress=False)


def pass_rates(report: EvaluationReport) -> dict[str, float]:
    totals: dict[str, list[bool]] = {}
    for case in report.cases:
        for name, result in case.assertions.items():
            totals.setdefault(name, []).append(bool(result.value))
    return {name: sum(v) / len(v) for name, v in totals.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None, help="pydantic-ai model id, or 'stand-in'")
    parser.add_argument("--baseline", default=None, help="second model to compare against")
    parser.add_argument("--name", default=None, help="experiment name, e.g. prompt-v2")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--gate", type=float, default=None, help="minimum RiskMatches pass rate")
    args = parser.parse_args()

    dataset = Dataset[dict, Any, dict].from_file(DATASET)
    dataset.evaluators = all_evaluators()
    dataset.report_evaluators = [risk_confusion_matrix]

    baseline = run(dataset, args.baseline, None, args.repeat) if args.baseline else None
    report = run(dataset, args.model, args.name, args.repeat)
    report.print(baseline=baseline, include_reasons=True)

    rates = pass_rates(report)
    print("\n" + "  ".join(f"{k}={v:.0%}" for k, v in rates.items()))
    if args.gate is not None:
        failed = [k for k in MUST_PASS if rates.get(k, 1.0) < 1.0]
        if rates.get("RiskMatches", 0.0) < args.gate:
            failed.append(f"RiskMatches<{args.gate:.0%}")
        if failed:
            print("GATE FAILED: " + ", ".join(failed))
            return 1
        print("GATE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
