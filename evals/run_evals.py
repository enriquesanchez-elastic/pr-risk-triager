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
import hashlib
import json
from datetime import datetime, timezone
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
from triager.triage import INSTRUCTIONS

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
        absent = sum(name not in c.assertions for c in report.cases)
        if not report.cases or absent == len(report.cases):
            failed.append(f"{name} produced no result")
        elif absent:
            failed.append(f"{name} missing on {absent} of {len(report.cases)} cases")
        elif rates[name] < 1.0:
            failed.append(name)
    if rates.get("RiskMatches", 0.0) < threshold:
        failed.append(f"RiskMatches<{threshold:.0%}")
    return failed


STAND_IN = Path(__file__).with_name("stand_in.py")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def save_report(report: Any, path: Path, model: str | None, prompt: str | None = None) -> None:
    """Persist one run so a later run can be compared against it: outputs, verdicts, and what produced them."""
    prompt = INSTRUCTIONS if prompt is None else prompt
    cases = {
        c.name: {
            "risk": c.output["risk"],
            "focus_areas": c.output["focus_areas"],
            "fallback_used": c.output.get("fallback_used"),
            "assertions": {k: bool(v.value) for k, v in c.assertions.items()},
        }
        for c in report.cases
    }
    meta = {
        "model": model,
        "judge": os.environ.get("JUDGE_MODEL"),
        "prompt_sha": _sha(prompt.encode()),
        "dataset_sha": _sha(DATASET.read_bytes()) if DATASET.exists() else None,
        # the stand-in's behaviour lives in its code, so its hash tells two stand-in runs apart
        "stand_in_sha": _sha(STAND_IN.read_bytes()) if STAND_IN.exists() else None,
        "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    path.write_text(json.dumps({**meta, "cases": cases}, indent=2))


def show_case(report: Any, name: str) -> str:
    """The model's actual answer for one case, so you can read what it put on the test list."""
    for c in report.cases:
        if c.name == name:
            areas = "\n".join(f"  - {a}" for a in c.output["focus_areas"])
            return f"{c.name}: risk {c.output['risk']}\nfocus areas:\n{areas}\nrationale: {c.output.get('rationale', '')}"
    return f"no case named {name!r}"


def diff_runs(report: Any, saved: Path) -> list[str]:
    """What changed against a saved run, per case: the risk label and every evaluator verdict that flipped."""
    old = json.loads(saved.read_text())["cases"]
    lines: list[str] = []
    for c in report.cases:
        before = old.get(c.name)
        if before is None:
            lines.append(f"{c.name}: not in the saved run")
            continue
        if before["risk"] != c.output["risk"]:
            lines.append(f"{c.name}: risk {before['risk']} -> {c.output['risk']}")
        for name, was in before["assertions"].items():
            now = bool(c.assertions[name].value) if name in c.assertions else None
            if now != was:
                lines.append(f"{c.name}: {name} {was} -> {now}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None, help="pydantic-ai model id, or 'stand-in'")
    parser.add_argument("--baseline", default=None, help="second model to compare against")
    parser.add_argument("--name", default=None, help="experiment name, e.g. prompt-v2")
    parser.add_argument("--show", default=None, metavar="CASE", help="print the model's output for one case")
    parser.add_argument("--save", type=Path, default=None, help="write this run to a JSON file")
    parser.add_argument("--against", type=Path, default=None, help="compare this run with a file saved by --save")
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

    if args.show:
        print("\n" + show_case(report, args.show))
    if args.save:
        save_report(report, args.save, model=args.model or os.environ.get("TRIAGER_MODEL", "gemini-3.7-flash"))
        print(f"saved to {args.save}")
    if args.against:
        changes = diff_runs(report, args.against)
        print("\nChanges against " + str(args.against) + ":\n  " + ("\n  ".join(changes) if changes else "none"))

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
