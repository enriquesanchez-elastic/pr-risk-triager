"""The gate is what the training tells people to trust, so it gets its own tests."""

from types import SimpleNamespace as NS

from evals.run_evals import gate_failures


def case(**assertions: bool) -> NS:
    return NS(assertions={k: NS(value=v) for k, v in assertions.items()}, evaluator_failures=[])


def report(cases: list[NS], failures: list | None = None) -> NS:
    return NS(cases=cases, failures=failures or [])


GOOD = dict(RiskMatches=True, NoUnderestimate=True, NotFallback=True)


def test_clean_run_passes():
    assert gate_failures(report([case(**GOOD)] * 5), 0.8) == []


def test_low_risk_accuracy_fails():
    cases = [case(**{**GOOD, "RiskMatches": False})] * 3 + [case(**GOOD)]
    assert any("RiskMatches" in f for f in gate_failures(report(cases), 0.8))


def test_underestimate_fails():
    assert "NoUnderestimate" in gate_failures(report([case(**{**GOOD, "NoUnderestimate": False})]), 0.8)


def test_crashed_required_evaluator_fails():
    # NoUnderestimate raised on every case: it produced no assertion at all.
    crashed = NS(assertions={k: NS(value=True) for k in ("RiskMatches", "NotFallback")}, evaluator_failures=[object()])
    failed = gate_failures(report([crashed] * 3), 0.8)
    assert "NoUnderestimate" in " ".join(failed)
    assert any("evaluator" in f for f in failed)


def test_task_failures_fail():
    failed = gate_failures(report([case(**GOOD)], failures=[object()]), 0.8)
    assert any("incomplete" in f for f in failed)
