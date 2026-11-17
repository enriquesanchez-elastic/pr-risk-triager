"""Step 5b: calibrate the judge before you trust it (needs the gateway and JUDGE_MODEL).

Four recorded outputs for ONE PR, with the verdict a careful human would give. If the judge
disagrees with you on any of them, its LLMJudge column cannot be trusted on real runs.

    JUDGE_MODEL=claude-sonnet-4-6 uv run python -m evals.check_judge
"""

from __future__ import annotations

import os
import sys
from typing import Any

from pydantic_evals import Case, Dataset

from evals.evaluators import focus_judge

MUST_COVER = ["users without alerts:all are rejected", "open alerts are not deleted"]
PR_INPUT = {
    "title": "Add bulk delete for closed alerts",
    "description": "New endpoint deletes closed alerts. Requires the alerts:all privilege.",
    "files": [],
}


def recorded(focus: list[str]) -> dict[str, Any]:
    return {"recorded": {"risk": "high", "focus_areas": focus, "rationale": "…", "fallback_used": False}, **PR_INPUT}


# case name -> (recorded focus areas, the verdict a careful human gives)
HUMAN: dict[str, tuple[list[str], bool]] = {
    "covers both": (["A user without alerts:all gets a 403", "Open alerts survive the bulk delete"], True),
    "covers one": (["A user without alerts:all gets a 403", "Delete button label is correct"], False),
    "different words, same behaviour": (
        ["Unprivileged callers are refused", "Alerts that are still open are never removed"],
        True,
    ),
    "specific but off topic": (["Pagination of the alerts table", "Alert tooltip copy matches the design"], False),
}


def main() -> int:
    judge = focus_judge()
    if judge is None:
        print("Set JUDGE_MODEL (e.g. claude-sonnet-4-6) and sign in with els first.")
        return 2
    dataset = Dataset[dict, Any, dict](
        name="judge-calibration",
        cases=[
            Case(name=name, inputs=recorded(focus), expected_output={"risk": "high", "must_cover": MUST_COVER})
            for name, (focus, _) in HUMAN.items()
        ],
        evaluators=[judge],
    )
    report = dataset.evaluate_sync(lambda inputs: inputs["recorded"], progress=False)
    disagreements = 0
    for case in report.cases:
        verdict = next(iter(case.assertions.values())).value
        human = HUMAN[case.name][1]
        mark = "agree" if verdict == human else "DISAGREE"
        disagreements += verdict != human
        print(f"{case.name:34} judge={'PASS' if verdict else 'FAIL'}  human={'PASS' if human else 'FAIL'}  {mark}")
    print(f"\n{disagreements} disagreement(s) out of {len(HUMAN)}")
    return 1 if disagreements else 0


if __name__ == "__main__":
    sys.exit(main())
