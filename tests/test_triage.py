"""Unit tests: they prove the plumbing works. They say nothing about triage quality."""

from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from triager import ChangedFile, PullRequest, TriageResult
from triager.triage import FALLBACK, render, triage

PR = PullRequest(
    title="Add pagination to the rules table",
    description="20 rules per page.",
    files=[ChangedFile(filename="rules_table.tsx", additions=120, deletions=40, patch="+ perPage: 20")],
)


def test_render_includes_title_files_and_patch():
    prompt = render(PR)
    assert "Add pagination to the rules table" in prompt
    assert "rules_table.tsx (+120 -40)" in prompt
    assert "+ perPage: 20" in prompt


def test_render_truncates_long_patches():
    big = PullRequest(title="t", files=[ChangedFile(filename="a.ts", patch="x" * 10_000)])
    assert len(render(big)) < 3_000


def test_triage_returns_a_valid_result():
    result = triage(PR, model=TestModel())
    assert isinstance(result, TriageResult)
    assert result.risk in {"low", "medium", "high"}


def test_triage_never_raises_when_the_model_fails():
    def broken(messages, info: AgentInfo):
        raise RuntimeError("model unavailable")

    assert triage(PR, model=FunctionModel(broken)) == FALLBACK
