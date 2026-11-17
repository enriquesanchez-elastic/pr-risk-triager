"""Step 2 — evaluate the evaluators before you trust them (no model needed).

Each case is a recorded output with a known verdict. If an evaluator can't tell
these apart, it can't tell real runs apart either.

    uv run python -m evals.check_evaluators
"""

from __future__ import annotations

from typing import Any

from pydantic_evals import Case, Dataset

from evals.evaluators import GENERIC, NotFallback, NoUnderestimate, RiskMatches, SpecificFocus

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

# Step 2a. Write your prediction BEFORE you run this file: fill in this table on paper, then compare.
EXPECTED: dict[str, dict[str, bool]] = {
    "right answer": {"RiskMatches": True, "NoUnderestimate": True, "SpecificFocus": True, "NotFallback": True},
    "over-cautious": {"RiskMatches": False, "NoUnderestimate": True, "SpecificFocus": True, "NotFallback": True},
    "dangerous miss": {"RiskMatches": False, "NoUnderestimate": False, "SpecificFocus": True, "NotFallback": True},
    "silent fallback": {"RiskMatches": True, "NoUnderestimate": True, "SpecificFocus": False, "NotFallback": False},
}


def verdicts() -> dict[str, dict[str, bool]]:
    report = dataset.evaluate_sync(lambda inputs: inputs["recorded"], progress=False)
    return {c.name: {k: bool(v.value) for k, v in c.assertions.items()} for c in report.cases}


def mismatches(expected: dict[str, dict[str, bool]] = EXPECTED) -> list[str]:
    """Every place an evaluator disagrees with the verdict we decided it should give."""
    got = verdicts()
    return [
        f"{case}: {name} gave {got[case].get(name)}, expected {want}"
        for case, wants in expected.items()
        for name, want in wants.items()
        if got[case].get(name) != want
    ]


# Step 2b. Where the checks are blind. Both outputs below are bad; a human would fail both.
BLIND = {
    "empty focus areas": {"risk": "high", "focus_areas": [], "rationale": "…", "fallback_used": False},
    "unrelated advice": {
        "risk": "high",
        "focus_areas": ["Verify the shopping checkout applies the discount code", "Test the cart badge count"],
        "rationale": "…",
        "fallback_used": False,
    },
}


def blind_spots() -> dict[str, bool]:
    """What SpecificFocus says about each bad output (True means it passed them)."""
    return {name: not any(GENERIC.search(a) for a in out["focus_areas"]) for name, out in BLIND.items()}


if __name__ == "__main__":
    dataset.evaluate_sync(lambda inputs: inputs["recorded"], progress=False).print(include_reasons=True)
    bad = mismatches()
    print("\nverdicts match the table" if not bad else "\nMISMATCH:\n  " + "\n  ".join(bad))
    print("\nBlind spots (SpecificFocus passes these bad outputs):")
    for name, passed in blind_spots().items():
        print(f"  {name}: SpecificFocus says {'PASS' if passed else 'FAIL'}; a human says FAIL")
    raise SystemExit(1 if bad else 0)
