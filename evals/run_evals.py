"""Steps 3-6 — run the triager over the dataset and score it.

    uv run python -m evals.run_evals --model stand-in                 # no gateway needed
    uv run python -m evals.run_evals                                  # gateway model (TRIAGER_MODEL or gemini-3.7-flash)
    JUDGE_MODEL=claude-sonnet-4-6 uv run python -m evals.run_evals    # + LLM judge
    uv run python -m evals.run_evals --repeat 3                       # run-to-run variance
    uv run python -m evals.run_evals --baseline stand-in              # compare against another model
    uv run python -m evals.run_evals --gate 0.8                       # exit 1 below the bar (CI)

Gateway models need an Okta token: run `els auth login --env $ELS_ENV` (default prod) first.
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
from triager.gateway import els_token

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
    model = model or os.environ.get("TRIAGER_MODEL", "gemini-3.7-flash")
    return stand_in_model if model == "stand-in" else model


def check_signed_in() -> None:
    """Get one gateway token up front, so els signs you in once instead of once per worker."""
    try:
        els_token()
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: no gateway token ({exc}). Every gateway call will fail and the triager will fall back.")


def run(dataset: Dataset, model: str | None, name: str | None, repeat: int) -> EvaluationReport:
    return dataset.evaluate_sync(make_task(resolve(model)), name=name or model, repeat=repeat, max_concurrency=4, progress=False)


def pass_rates(report: EvaluationReport) -> dict[str, float]:
    totals: dict[str, list[bool]] = {}
    for case in report.cases:
        for name, result in case.assertions.items():
            totals.setdefault(name, []).append(bool(result.value))
    return {name: sum(v) / len(v) for name, v in totals.items()}


def gate_failures(report: EvaluationReport, threshold: float) -> list[str]:
    """Why the gate should fail. Empty list = pass. A missing or crashed result is a failure, never a pass."""
    failed: list[str] = []
    if report.failures:
        failed.append(f"incomplete run ({len(report.failures)} cases crashed)")
    broken = sum(len(c.evaluator_failures) for c in report.cases)
    if broken:
        failed.append(f"{broken} evaluator errors")
    rates = pass_rates(report)
    for name in MUST_PASS:
        if name not in rates:
            failed.append(f"{name} produced no result")
        elif rates[name] < 1.0:
            failed.append(name)
    if rates.get("RiskMatches", 0.0) < threshold:
        failed.append(f"RiskMatches<{threshold:.0%}")
    return failed


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

    models = [args.model or os.environ.get("TRIAGER_MODEL", "gemini-3.7-flash"), args.baseline]
    if any(m and m != "stand-in" for m in models) or os.environ.get("JUDGE_MODEL"):
        check_signed_in()
    baseline = run(dataset, args.baseline, None, args.repeat) if args.baseline else None
    report = run(dataset, args.model, args.name, args.repeat)
    report.print(baseline=baseline, include_reasons=True)

    rates = pass_rates(report)
    print("\n" + "  ".join(f"{k}={v:.0%}" for k, v in rates.items()))
    if args.gate is not None:
        failed = gate_failures(report, args.gate)
        if failed:
            print("GATE FAILED: " + ", ".join(failed))
            return 1
        print("GATE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
