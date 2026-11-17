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
| `evals/check_judge.py` | Calibrate the LLM judge against 4 outputs a human has labelled (needs the gateway) |
| `evals/run_evals.py` | The eval: `--model`, `--baseline`, `--repeat`, `--gate`, `--name`, `--save`, `--against` |
| `evals/stand_in.py` | A weak keyword model for running without the gateway |

### A1. See the gap (2 min)

```bash
uv run pytest
uv run triage examples/pr_pagination.json
```

Tests pass and the CLI prints a triage. No gateway access? Use the offline model: `uv run triage examples/pr_pagination.json --model stand-in`. **Check the output is a real answer.** If the gateway call failed, the triager logs `using fallback` and prints a canned result: risk `medium` with "General regression testing" as the focus. That result looks plausible and is not an analysis. A medium rating on the pagination PR is also what the labeller expects, so the fallback can look right for the wrong reason. This is the failure A3 is built to catch. Now answer: would you let this rate PRs for your team? What would you need to see first?

### A2. The dataset (4 min)

Open `evals/dataset.yaml`. Each case has the PR as `inputs` and an `expected_output` that is a spec, not an exact answer: the risk label plus `must_cover`, the behaviours a QA engineer would insist on.

Note the mix: typical changes, edge cases (docs, refactor, devDependency bump), a migration whose title says "rename", and a typo fix whose description tries to inject instructions.

Add one case from your own team's recent PRs. Agree its label with your neighbour. If you disagree, that disagreement is the most useful thing in the dataset.

Your edit stays in your working tree. Before you switch to the `lab-b` branch, undo it with `git restore evals/dataset.yaml` (or keep it with `git stash`), or Git will refuse to switch.

### A3. Evaluators, checked before you trust them (4 min)

**Predict first.** Before you run anything, copy the table below onto paper with the cells empty and fill in what you expect each evaluator to say for each recorded case (open `evals/check_evaluators.py` to see the four outputs, but not the `EXPECTED` table). Then run:

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

The script now asserts this table (`EXPECTED` in the file) and exits 1 if an evaluator disagrees, so you can change an evaluator and see at once what moved. Count your wrong cells: each is a place where you would have trusted a check that does something else.

The last row is the lesson: the canned fallback gets the risk right for the wrong reason. Only `SpecificFocus` and `NotFallback` catch it.

**Blind spots.** The script ends by showing two outputs a human would fail, and `SpecificFocus` passes both: an empty focus list, and focus areas about a shopping checkout for an alerts PR. `SpecificFocus` only catches boilerplate such as "General regression testing"; it is a heuristic, not a measure of quality. Say which check in A5 is meant to catch these.

### A4. Run the triager (4 min)

```bash
uv run python -m evals.run_evals --model stand-in
```

**Read one failure.** In the table, pick one case where `RiskMatches` is ✗. Open its `must_cover` in `evals/dataset.yaml` and its output in the report. In one sentence: which behaviour did the model miss, and why did the keyword rule fire? (For `rule-schedule-migration` the word "rename" in the title decides it.)

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

**Calibrate the judge** (signed in): `JUDGE_MODEL=claude-sonnet-4-6 uv run python -m evals.check_judge`. It runs the judge on four outputs for one PR that a human has labelled: one covers both required behaviours, one covers only one, one covers both in different words, one is specific but off topic. Predict the judge's four verdicts first. Any disagreement with the human labels means the `LLMJudge` column is not yet trustworthy: tighten the rubric in `focus_judge()` and run it again.

### A6. Repeat and gate (2 min)

```bash
uv run python -m evals.run_evals --model stand-in --repeat 3 --gate 0.8
echo $?
```

Each case runs 3 times, so you see the spread. (Without `--model stand-in` the same command runs the default gateway model.) The gate exits 1 if any fallback happened, any risk was under-rated, `RiskMatches` is below 80%, or the run is incomplete (a case or an evaluator crashed, or a required score is missing). A missing result never counts as a pass. With the stand-in it fails on `NoUnderestimate`, as it should.

With the real default model (`uv run python -m evals.run_evals --repeat 3 --gate 0.8`, signed in) the gate passes: all four code evaluators 100%, `GATE PASSED`, exit 0. Try the other families:

```bash
JUDGE_MODEL=claude-sonnet-4-6 uv run python -m evals.run_evals --model gpt-5.4 --repeat 3 --gate 0.8
```

We measured: `claude-sonnet-4-6` passes (`LLMJudge` 93%; note it is judged by its own family, so prefer a Gemini or GPT judge for it); `gpt-5.4` **fails** `NoUnderestimate`, in every run we saw. In one run: `RiskMatches` 90%, `NoUnderestimate` 90%, `LLMJudge` 83%, with 3 misses in 30 runs, all `viewer-api-keys`, a `high` PR that GPT rates `medium`. In a second run: `RiskMatches` 93%, `NoUnderestimate` 93%, `SpecificFocus` 90%, `LLMJudge` 93%, with 2 misses in 30 runs. The scores move by a few points between runs; the gate result should not. Your numbers will differ. Same PRs, same prompt, different model: that is the case for evals.

**Change one thing, compare.** Save a baseline, change one thing, run again against it, with the dataset and model fixed:

```bash
uv run python -m evals.run_evals --model stand-in --save before.json
# edit evals/stand_in.py: delete "rename" from the LOW keywords
uv run python -m evals.run_evals --model stand-in --against before.json
```

The report lists every case whose risk or verdict changed. Deleting `rename` fixes `rule-schedule-migration` (NoUnderestimate goes to 100%) and breaks `rename-internal-hook`, so `RiskMatches` does not move: one fix traded for one new miss. `before.json` records the model, a hash of the prompt and of the dataset, and a timestamp, so you can tell later what produced it. With a real model, change `INSTRUCTIONS` in `src/triager/triage.py` instead and compare the same way. Note that `--baseline` is different: it runs a second model now, it does not load a saved run.

Open `.github/workflows/evals.yml`. What you have built is a local gate. In CI the workflow runs the stand-in as a pipeline check and does not yet enforce a quality threshold, so a failing score does not fail the job today. The real gate needs a gateway identity CI can use: not `els` (that is for people), but an approved GCP service account with a Google ID token, as the comments in the workflow explain.

## Broke something?

Restore the finished files: `git checkout origin/lab-a -- evals/`. Troubleshooting is in [GUIDE.md](GUIDE.md).
