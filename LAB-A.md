# Lab A: from zero evals to a CI gate

Start here:

```bash
git checkout lab-a
uv sync
```

Lab A needs Python 3.12 and uv. From step A4 on, the real model needs `els auth login --env prod` (optional: `--model stand-in` runs without it). The settings table is in [GUIDE.md](GUIDE.md).

You finish Lab A with an `evals/` folder: a 10-case dataset, four code evaluators, an optional LLM judge, a confusion matrix and a gate that fails CI. Every file is already in `evals/` on this branch, so you spend the time reading and running, not typing. All commands run from the repo root on `lab-a`.

| File | What it holds |
| --- | --- |
| `evals/dataset.yaml` | 10 labelled PRs: inputs, expected risk, `must_cover`, metadata |
| `evals/evaluators.py` | `RiskMatches`, `NoUnderestimate`, `SpecificFocus`, `NotFallback`, `focus_judge()`, the confusion matrix |
| `evals/check_evaluators.py` | The evaluators run on 4 recorded outputs, no model |
| `evals/run_evals.py` | The eval: `--model`, `--baseline`, `--repeat`, `--gate`, `--name` |
| `evals/stand_in.py` | A weak keyword model for running without the gateway |

### A1. See the gap (2 min)

```bash
uv run pytest
uv run triage examples/pr_pagination.json
```

Tests pass and the CLI prints a triage. Now answer: would you let this rate PRs for your team? What would you need to see first?

### A2. The dataset (4 min)

Open `evals/dataset.yaml`. Each case has the PR as `inputs` and an `expected_output` that is a spec, not an exact answer: the risk label plus `must_cover`, the behaviours a QA engineer would insist on.

Note the mix: typical changes, edge cases (docs, refactor, devDependency bump), a migration whose title says "rename", and a typo fix whose description tries to inject instructions.

Add one case from your own team's recent PRs. Agree its label with your neighbour. If you disagree, that disagreement is the most useful thing in the dataset.

### A3. Evaluators, checked before you trust them (4 min)

```bash
uv run python -m evals.check_evaluators
```

Open `evals/evaluators.py` and `evals/check_evaluators.py`. Each evaluator answers one question. The check runs them on four recorded outputs with known verdicts, so no model is called. Expected:

| Recorded case | RiskMatches | NoUnderestimate | SpecificFocus | NotFallback |
| --- | --- | --- | --- | --- |
| right answer | ✔ | ✔ | ✔ | ✔ |
| over-cautious | ✗ | ✔ | ✔ | ✔ |
| dangerous miss | ✗ | ✗ | ✔ | ✔ |
| silent fallback | ✔ | ✔ | ✗ | ✗ |

The last row is the lesson: the canned fallback gets the risk right for the wrong reason. Only `SpecificFocus` and `NotFallback` catch it.

### A4. Run the triager (4 min)

```bash
uv run python -m evals.run_evals --model stand-in
```

Open `evals/run_evals.py` (and `evals/stand_in.py`): the `task` function is the whole integration. It calls `triage()` and records one signal from inside the tool: whether the "using fallback" warning fired.

If you added a case in A2, your percentages shift by one case. The stand-in scores `RiskMatches` 80%, `NoUnderestimate` 90%, `SpecificFocus` 20%, `NotFallback` 100%. Find the two misses in the table and the confusion matrix:

- it under-rates the migration (the word "rename" fooled it)
- it obeys the instruction hidden in the typo PR

Signed in, run the real model through the gateway:

```bash
uv run python -m evals.run_evals --name baseline
uv run python -m evals.run_evals --model claude-sonnet-4-6    # or gpt-5.4
```

Then simulate being signed out:

```bash
ELS_BIN=false uv run python -m evals.run_evals
```

The preflight warns, but the run completes and nothing crashes: every PR comes back `medium`. Every case now fails `NotFallback` and `SpecificFocus` (both 0%), and the label scores collapse too: `RiskMatches` 20%, `NoUnderestimate` 70% (the three `high` PRs are rated `medium`). Without `NotFallback` you would only see the label scores drop, with no hint that the model never ran.

With Gemini 3.7 Flash the baseline scores 100% on all four code evaluators. A perfect score on 10 cases is a ceiling, not proof the triager is good: which cases would you add to make it fail?

### A5. Judge and compare (2 min)

Code checks the label; only a judge can say whether the focus areas cover `must_cover`. Use a different model family from the one being evaluated.

```bash
JUDGE_MODEL=claude-sonnet-4-6 uv run python -m evals.run_evals --baseline stand-in
```

`--baseline` runs a second model and prints a per-case diff, so you see which cases a change fixed and which it broke.

With Gemini as the model and Claude as judge, expect `LLMJudge` around 90%.

### A6. Repeat and gate (2 min)

```bash
uv run python -m evals.run_evals --model stand-in --repeat 3 --gate 0.8
echo $?
```

Each case runs 3 times, so you see the spread. (Without `--model stand-in` the same command runs the default gateway model.) The gate exits 1 if any fallback happened, any risk was under-rated, or `RiskMatches` is below 80%. With the stand-in it fails on `NoUnderestimate`, as it should.

With the real default model (`uv run python -m evals.run_evals --repeat 3 --gate 0.8`, signed in) the gate passes: all four code evaluators 100%, `GATE PASSED`, exit 0. Try the other families:

```bash
JUDGE_MODEL=claude-sonnet-4-6 uv run python -m evals.run_evals --model gpt-5.4 --repeat 3 --gate 0.8
```

We measured: `claude-sonnet-4-6` passes (`LLMJudge` 93%; note it is judged by its own family, so prefer a Gemini or GPT judge for it); `gpt-5.4` **fails** (`RiskMatches` 90%, `NoUnderestimate` 90%, `LLMJudge` 83%). The miss is the same case on all 3 repeats: `viewer-api-keys`, a `high` PR that GPT rates `medium`. Same PRs, same prompt, different model: that is the case for evals.

Open `.github/workflows/evals.yml`. It runs the stand-in on every PR. The real gate needs a gateway identity CI can use: not `els` (that is for people), but an approved GCP service account with a Google ID token, as the comments in the workflow explain.

## Broke something?

Restore the finished files: `git checkout origin/lab-a -- evals/`. Troubleshooting is in [GUIDE.md](GUIDE.md).
