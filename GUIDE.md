# Evals Lab Guide: pr-risk-triager

## Before you start

In 25 minutes you take a small AI tool with green CI and no evals to an eval suite with a CI gate, then rebuild the same eval in @kbn/evals.

The tool is `pr-risk-triager`: give it a pull request and it returns a risk level (`low`, `medium`, `high`), up to 5 focus areas for QA, and a rationale. It is one LLM call through pydantic-ai and Elastic's LLM gateway (AgentRouter).

| Part | Time | Needs |
| --- | --- | --- |
| Lab A: Python + pydantic-evals | 18 min | Python 3.12, uv; `els` signed in to the gateway from step A4 on (optional) |
| Lab B: @kbn/evals | 7 min | Kibana bootstrapped, `vault login --method oidc` for EIS models |

The repo has two branches. `main` is the starting point: the tool, 8 unit tests, CI running pytest, no evals. `solution` holds every file you write in Lab A. Fall behind? `git checkout solution` and carry on.

### Set up before the session

- [ ] Clone the repo, run `uv sync`, then `uv run pytest` (8 passed)
- [ ] Run `uv add --dev pydantic-evals`
- [ ] Run `els auth login --env prod` once. You must be in exactly one `AgentRouter - <tier>` Okta group. Use `ELS_ENV=dev` or `test` for another environment (test allows 27,500 tokens per hour: too few for a full run with the judge)
- [ ] Lab B only: `yarn kbn bootstrap` in Kibana, then `node scripts/evals doctor`

Not signed in? Every step except the LLM judge runs with `--model stand-in`, a deliberately weak keyword model in `evals/stand_in.py`. Its scores say nothing about the real triager; it exists so the pipeline runs anywhere.

There are no API keys anywhere in the repo. Every real model call goes through the gateway with your `els` token.

| Setting | Default | What it does |
| --- | --- | --- |
| `ELS_ENV` | `prod` | Gateway environment: `dev`, `test`, `prod` |
| `ELS_BIN` | `els` | Path to `els` if it is not on your PATH |
| `TRIAGER_MODEL` / `--model` | `gemini-3.7-flash` | Model being evaluated: any gateway model name |
| `JUDGE_MODEL` | unset | Model for the LLM judge. Use a different family from the one being evaluated |

Model families that work through the gateway: Gemini and Claude (chat completions), GPT (Responses API). `src/triager/gateway.py` handles both.

## Lab A: from zero evals to a CI gate

You finish Lab A with an `evals/` folder: a 10-case dataset, four code evaluators, an optional LLM judge, a confusion matrix and a gate that fails CI. Each step pulls one or two files from `solution`, so you spend the time reading and running, not typing. All commands run from the repo root on `main`.

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

```bash
git checkout origin/solution -- evals/__init__.py evals/dataset.yaml
```

Read `evals/dataset.yaml`. Each case has the PR as `inputs` and an `expected_output` that is a spec, not an exact answer: the risk label plus `must_cover`, the behaviours a QA engineer would insist on.

Note the mix: typical changes, edge cases (docs, refactor, devDependency bump), a migration whose title says "rename", and a typo fix whose description tries to inject instructions.

Add one case from your own team's recent PRs. Agree its label with your neighbour. If you disagree, that disagreement is the most useful thing in the dataset.

### A3. Evaluators, checked before you trust them (4 min)

```bash
git checkout origin/solution -- evals/evaluators.py evals/check_evaluators.py
uv run python -m evals.check_evaluators
```

Each evaluator answers one question. The check runs them on four recorded outputs with known verdicts, so no model is called. Expected:

| Recorded case | RiskMatches | NoUnderestimate | SpecificFocus | NotFallback |
| --- | --- | --- | --- | --- |
| right answer | ✔ | ✔ | ✔ | ✔ |
| over-cautious | ✗ | ✔ | ✔ | ✔ |
| dangerous miss | ✗ | ✗ | ✔ | ✔ |
| silent fallback | ✔ | ✔ | ✗ | ✗ |

The last row is the lesson: the canned fallback gets the risk right for the wrong reason. Only `SpecificFocus` and `NotFallback` catch it.

### A4. Run the triager (4 min)

```bash
git checkout origin/solution -- evals/run_evals.py evals/stand_in.py
uv run python -m evals.run_evals --model stand-in
```

Open `run_evals.py`: the `task` function is the whole integration. It calls `triage()` and records one signal from inside the tool: whether the "using fallback" warning fired.

The stand-in scores `RiskMatches` 80%, `NoUnderestimate` 90%, `SpecificFocus` 20%, `NotFallback` 100%. Find the two misses in the table and the confusion matrix:

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

The preflight warns, but the run completes: every PR comes back `medium`, nothing crashes, and only `NotFallback` (0%) and `SpecificFocus` (0%) say so.

### A5. Judge and compare (2 min)

Code checks the label; only a judge can say whether the focus areas cover `must_cover`. Use a different model family from the one being evaluated.

```bash
JUDGE_MODEL=claude-sonnet-4-6 uv run python -m evals.run_evals --baseline stand-in
```

`--baseline` runs a second model and prints a per-case diff, so you see which cases a change fixed and which it broke.

### A6. Repeat and gate (2 min)

```bash
uv run python -m evals.run_evals --repeat 3 --gate 0.8
echo $?
git checkout origin/solution -- .github/workflows/evals.yml
```

Each case runs 3 times, so you see the spread. The gate exits 1 if any fallback happened, any risk was under-rated, or `RiskMatches` is below 80%. With the stand-in it fails on `NoUnderestimate`, as it should.

`evals.yml` runs the stand-in on every PR. The real gate needs a gateway identity CI can use: not `els` (that is for people), but an approved GCP service account with a Google ID token, as the comments in the workflow explain.

## Lab B: the same eval in @kbn/evals

You finish Lab B with the triage eval running as a Kibana suite: three PRs, three code evaluators, the criteria judge and token counts, stored as an experiment in the evals UI. The spec is in the repo at `kbn-evals/evals/pr_triage.spec.ts`. Commands run from the Kibana repo root.

Lab B calls models through Kibana connectors, not the LLM gateway, so `els` is not involved.

### B1. Validate your setup (2 min)

```bash
node scripts/evals start --suite smoke-tests --profile local
```

The first run asks for connectors, starts Scout and the EDOT collector, and runs the smoke suite; later runs reuse the services. If it fails, run `node scripts/evals doctor`.

### B2. Add the spec and read it (2 min)

Scaffold a suite named `lab` with the `evals-create-suite` agent skill, then copy `kbn-evals/playwright.config.ts` and `kbn-evals/evals/pr_triage.spec.ts` into it. Match the spec to the anatomy:

1. **Dataset**: three PRs. The expected risk sits in each example's `output`; `mustCover` sits in `metadata`, because the criteria judge reads input, output and metadata.
2. **Task**: one `inferenceClient.chatComplete` call, bound to the model of the current Playwright project, asking for JSON.
3. **Evaluators**: `ValidJson`, `RiskMatches` and `NoUnderestimate` (CODE, each with `direction: 'maximize'`), `evaluators.criteria([...])` named `FocusCoverage`, and the trace-based `inputTokens` and `outputTokens`.

### B3. Run it against two models (2 min)

```bash
node scripts/evals start --profile local \
  --config x-pack/platform/packages/shared/kbn-evals-suite-lab/playwright.config.ts \
  --model <connector-a>,<connector-b> --judge <judge-connector>
```

The suite isn't registered in `evals.suites.json`, so `--config` points at it directly. Connector ids come from `node scripts/evals init`. Pick a judge from a different family than both models.

### B4. Compare in the UI (1 min)

In the Kibana your profile exports to (local: the URL in `config.local.json`), open `/app/management/ai/evals` → Experiments, select the two runs and use **Compare selected** (a paired t-test per evaluator), or run `node scripts/evals compare <exp-1> <exp-2>`. The Tracing tab shows the spans the token evaluators read.

## Stretch goals

If you finish early, pick one.

- [ ] Make the fallback visible: change `triage()` to return a `source` field (`"llm"` or `"fallback"`), then simplify `NotFallback` to read it instead of the log.
- [ ] Change the prompt in `triage.py` (say, "data migrations are always high"), re-run with `--name prompt-v2`, and compare `RiskMatches` and `NoUnderestimate` with your baseline run.
- [ ] Add a second adversarial case: a PR whose description tries to hide a permissions change.
- [ ] Run the judge twice on the same outputs and count how often it changes its verdict: that is your judge's noise floor.
- [ ] Lab B: add `--repetitions 3` and compare the spread of `FocusCoverage` between the two models.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `ModuleNotFoundError: pydantic_evals` | Not in the repo's env | `uv add --dev pydantic-evals` |
| `ModuleNotFoundError: evals.stand_in` | Step A4 files not pulled | `git checkout origin/solution -- evals/run_evals.py evals/stand_in.py` |
| Every case `NotFallback: ✗` | Not signed in to the gateway, or `els` not on PATH | `els auth login --env $ELS_ENV`; set `ELS_BIN` to `els`' full path |
| Gateway 401 | Token expired | Run `els auth login` again |
| Gateway 403 "RBAC: access denied" | Token from another environment than `ELS_ENV`, or not in exactly one AgentRouter group | Match `ELS_ENV` to your login; check your Okta groups |
| Gateway 404 "No matching route found" | Model name not exact | Copy the name from the gateway's model table (`els models`) |
| Gateway 429 | Usage limit (test: 27,500 tokens per hour per person; dev: daily budget per tier) | Wait for the hourly reset, drop `--repeat`, or use prod |
| Gateway 400 "Organization Policy ... structured_outputs" (Claude) | Strict tool schemas are blocked for Claude on Vertex | Already handled in `src/triager/gateway.py` on `main`; don't replace it with an older copy |
| No `LLMJudge` column | `JUDGE_MODEL` unset | Set it to a gateway model name, e.g. `claude-sonnet-4-6` |
| `expected_output … valid list` error | Dataset typed with a list output | Keep `Dataset[dict, Any, dict]` |
| "No connectors found" (Lab B) | Not in a TTY, or stale cache | Run in a terminal; `rm ~/.elastic/eis-connectors-cache.json` |
| Scout hangs on start | Old services still running | `node scripts/evals stop`, then retry |
| 429 errors in Lab B | Too many concurrent calls | Lower `--concurrency` |
