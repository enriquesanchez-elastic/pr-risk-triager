"""Evaluators for the triager. Each one answers ONE question about one output.

Task output shape: TriageResult as a dict, plus "fallback_used" (bool, or None when not instrumented).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

from pydantic_evals.evaluators import ConfusionMatrixEvaluator, EvaluationReason, Evaluator, EvaluatorContext, LLMJudge

from triager.gateway import gateway_model

Output = dict[str, Any]
RISK_ORDER = {"low": 0, "medium": 1, "high": 2}
GENERIC = re.compile(r"general regression|^test (the )?changes|^smoke test|^verify (the )?(feature|functionality)", re.I)


@dataclass
class RiskMatches(Evaluator[dict, Output]):
    """Classification: did we get the risk level the labeller gave?"""

    def evaluate(self, ctx: EvaluatorContext[dict, Output]) -> dict[str, EvaluationReason | str]:
        got, want = ctx.output["risk"], ctx.expected_output["risk"]
        return {
            "RiskMatches": EvaluationReason(value=got == want, reason=f"got {got}, expected {want}"),
            "predicted_risk": got,  # labels, read by the confusion matrix
            "labelled_risk": want,
        }


@dataclass
class NoUnderestimate(Evaluator[dict, Output]):
    """Errors are not equal: calling a high-risk PR 'low' is the one that ships bugs."""

    def evaluate(self, ctx: EvaluatorContext[dict, Output]) -> EvaluationReason:
        got, want = ctx.output["risk"], ctx.expected_output["risk"]
        ok = RISK_ORDER[got] >= RISK_ORDER[want]
        return EvaluationReason(value=ok, reason="ok" if ok else f"rated {got}, labelled {want}")


@dataclass
class SpecificFocus(Evaluator[dict, Output]):
    """No boilerplate focus areas like 'General regression testing'."""

    def evaluate(self, ctx: EvaluatorContext[dict, Output]) -> EvaluationReason:
        generic = [a for a in ctx.output["focus_areas"] if GENERIC.search(a)]
        return EvaluationReason(value=not generic, reason="; ".join(generic) or "all specific")


@dataclass
class NotFallback(Evaluator[dict, Output]):
    """Did the model actually answer? triage() swallows errors and returns a canned result."""

    def evaluate(self, ctx: EvaluatorContext[dict, Output]) -> EvaluationReason:
        used = ctx.output.get("fallback_used")
        if used is None:
            return EvaluationReason(value=False, reason="not instrumented: fallback_used missing, so unknown")
        return EvaluationReason(value=not used, reason="fallback result" if used else "model answered")


def focus_judge() -> LLMJudge | None:
    """LLM-as-a-judge for what code can't check: are the right things on the test list?

    Enabled when JUDGE_MODEL is set to a gateway model, e.g. claude-sonnet-4-6.
    Use a different model family from the one being evaluated (the triager defaults to Gemini).
    """
    model = os.environ.get("JUDGE_MODEL")
    if not model:
        return None
    return LLMJudge(
        rubric=(
            "The output is a QA triage of the pull request in the input. "
            "PASS if focus_areas cover every behaviour in expected_output.must_cover (wording may differ) "
            "and every focus area is specific to this PR. If must_cover is empty, PASS only if the "
            "focus areas are few and proportionate to a low-risk change."
        ),
        model=gateway_model(model),
        include_input=True,
        include_expected_output=True,
    )


def all_evaluators() -> list[Evaluator]:
    judge = focus_judge()
    return [RiskMatches(), NoUnderestimate(), SpecificFocus(), NotFallback(), *([judge] if judge else [])]


# Runs once over the whole experiment, not per case.
risk_confusion_matrix = ConfusionMatrixEvaluator(
    predicted_from="labels",
    predicted_key="predicted_risk",
    expected_from="labels",
    expected_key="labelled_risk",
    title="Risk: labelled (rows) vs predicted (columns)",
)
