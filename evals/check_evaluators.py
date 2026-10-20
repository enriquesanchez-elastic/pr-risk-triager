"""Step 2 — evaluate the evaluators before you trust them (no model needed).

Each case is a recorded output with a known verdict. If an evaluator can't tell
these apart, it can't tell real runs apart either.

    uv run python -m evals.check_evaluators
"""

from __future__ import annotations

from typing import Any

from pydantic_evals import Case, Dataset

from evals.evaluators import NotFallback, NoUnderestimate, RiskMatches, SpecificFocus

DELETE_PR = {"must_cover": ["users without alerts:all are rejected", "open alerts are not deleted"]}


def recorded(risk: str, focus: list[str], fallback: bool | None = False) -> dict[str, Any]:
    return {"recorded": {"risk": risk, "focus_areas": focus, "rationale": "…", "fallback_used": fallback}}


dataset = Dataset[dict, Any, dict](
    name="evaluator-sanity",
    cases=[
        Case(
            name="right answer",
            inputs=recorded("high", ["Users without alerts:all get a 403", "Open alerts survive the bulk delete"]),
            expected_output={"risk": "high", **DELETE_PR},
        ),
        Case(
            name="over-cautious",
            inputs=recorded("high", ["Tooltip text matches the copy deck"]),
            expected_output={"risk": "low", "must_cover": []},
        ),
        Case(
            name="dangerous miss",
            inputs=recorded("low", ["Button label reads 'Delete closed alerts'"]),
            expected_output={"risk": "high", **DELETE_PR},
        ),
        Case(
            name="silent fallback",
            inputs=recorded("medium", ["General regression testing of the changed files"], fallback=True),
            expected_output={"risk": "medium", "must_cover": ["sorting resets to page 1"]},
        ),
    ],
    evaluators=[RiskMatches(), NoUnderestimate(), SpecificFocus(), NotFallback()],
)

if __name__ == "__main__":
    dataset.evaluate_sync(lambda inputs: inputs["recorded"], progress=False).print(include_reasons=True)
