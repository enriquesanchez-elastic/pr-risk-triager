# Evals Lab Guide: pr-risk-triager

## Before you start

The session takes under 50 minutes, 25 of them hands-on. You take a small AI tool with green CI and no evals to an eval suite with a CI gate (Lab A), then run the same eval as a Kibana suite and compare two models (Lab B).

The tool is `pr-risk-triager`: give it a pull request and it returns a risk level (`low`, `medium`, `high`), up to 5 focus areas for QA, and a rationale. It is one LLM call through pydantic-ai and Elastic's LLM gateway (AgentRouter).

## Which branch, which guide

| Part | Time | Branch | Guide | Needs |
| --- | --- | --- | --- | --- |
| Lab A: Python + pydantic-evals | 18 min | `lab-a` | [`LAB-A.md`](https://github.com/enriquesanchez-elastic/pr-risk-triager/blob/lab-a/LAB-A.md) | Python 3.12, uv; `els` signed in to the gateway from step A4 on (optional) |
| Evals in Kibana (walkthrough) | 5 min | none | slides | Nothing |
| Lab B: @kbn/evals | 7 min | `lab-b` | [`LAB-B.md`](https://github.com/enriquesanchez-elastic/pr-risk-triager/blob/lab-b/LAB-B.md) | A Kibana checkout, bootstrapped; `vault login --method oidc` for EIS models |

`main` is the starting point: the tool, 8 unit tests, CI running pytest, no evals. Lab A is on `lab-a` (`main` plus the full `evals/` folder). Lab B is on `lab-b` (`main` plus `kbn-evals/`; its files are copied into a Kibana checkout).

### Set up before the session

- [ ] Clone the repo (`git clone https://github.com/enriquesanchez-elastic/pr-risk-triager.git`; it is private, so you need read access), run `uv sync`, then `uv run pytest` (8 passed)
- [ ] Run `git checkout lab-a`, then `uv sync` again (this installs `pydantic-evals`)
- [ ] Run `els auth login --env prod` once. You must be in exactly one `AgentRouter - <tier>` Okta group. Use `ELS_ENV=dev` or `test` for another environment (test allows 27,500 tokens per hour: too few for a full run with the judge)
- [ ] Lab B only, in a clean Kibana worktree: `corepack enable` and `corepack prepare pnpm@12.4.2 --activate` (first time only), then `pnpm kbn bootstrap` (older Kibana checkouts use `yarn kbn bootstrap`), then `node scripts/evals doctor`. Scout and the EDOT collector show as not running until B1 starts them

Not signed in? Every Lab A step except the LLM judge runs with `--model stand-in`, a deliberately weak keyword model in `evals/stand_in.py`. Its scores say nothing about the real triager; it exists so the pipeline runs anywhere.

There are no API keys anywhere in the repo. Every real model call in Lab A goes through the gateway with your `els` token.

| Setting | Default | What it does |
| --- | --- | --- |
| `ELS_ENV` | `prod` | Gateway environment: `dev`, `test`, `prod` |
| `ELS_BIN` | `els` | Path to `els` if it is not on your PATH |
| `TRIAGER_MODEL` / `--model` | `gemini-3.7-flash` | Model being evaluated: any gateway model name |
| `JUDGE_MODEL` | unset | Model for the LLM judge. Use a different family from the one being evaluated |

Model families that work through the gateway: Gemini and Claude (chat completions), GPT (Responses API). `src/triager/gateway.py` handles both.

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
| `ModuleNotFoundError: pydantic_evals` | Still on `main`, or `uv sync` not run after switching | `git checkout lab-a`, then `uv sync` |
| `ModuleNotFoundError: evals.stand_in` | Not on the `lab-a` branch, or `evals/` was changed | `git checkout lab-a`, then `git checkout origin/lab-a -- evals/` |
| Every case `NotFallback: ✗` | Not signed in to the gateway, or `els` not on PATH | `els auth login --env $ELS_ENV`; set `ELS_BIN` to `els`' full path |
| Gateway 401 | Token expired | Run `els auth login` again |
| Gateway 403 "RBAC: access denied" | Token from another environment than `ELS_ENV`, or not in exactly one AgentRouter group | Match `ELS_ENV` to your login; check your Okta groups |
| Gateway 404 "No matching route found" | Model name not exact | Copy the name from the gateway's model table (`els models`) |
| Gateway 429 | Usage limit (test: 27,500 tokens per hour per person; dev: daily budget per tier) | Wait for the hourly reset, drop `--repeat`, or use prod |
| Gateway 400 "Organization Policy ... structured_outputs" (Claude) | Strict tool schemas are blocked for Claude on Vertex | Already handled in `src/triager/gateway.py` on `main`; don't replace it with an older copy |
| No `LLMJudge` column | `JUDGE_MODEL` unset | Set it to a gateway model name, e.g. `claude-sonnet-4-6` |
| `expected_output … valid list` error | Dataset typed with a list output | Keep `Dataset[dict, Any, dict]` |
| "No connectors found" (Lab B) | Not in a TTY, or stale cache | Run in a terminal; `rm ~/.elastic/eis-connectors-cache.json` |
| `EVAL_CONNECTOR_ID is required` (Lab B) | No TTY, so no connector prompt | Pass `--evaluation-connector-id <id>` and `--model <id>` |
| `Project(s) "<id>" not found` (Lab B) | `--model` is not a Playwright project of the suite | Pick an id from the error's list |
| `fetch failed` on `localhost:5601/dev/...` (Lab B) | Local profile points at a dev Kibana that isn't running | Start it, or point `config.local.json` at Scout's `:9220`/`:5620` (see B4) |
| `pnpm is required` / Yarn "configured to use pnpm" (Lab B) | Corepack not enabled | `corepack enable`, `corepack prepare pnpm@12.4.2 --activate`, then `pnpm kbn bootstrap` |
| `Inference with id … already exists` 500 on connector create (Lab B) | Seen on a long-lived Kibana checkout with local, uncommitted evals code; upstream `main` in a clean `git worktree` worked | Retry in a clean worktree on `origin/main` (`git worktree add ../kibana-clean origin/main --detach`, then bootstrap) |
| Tokens column `-`, `Unknown column [trace.id]` in the run log (Lab B) | The EDOT collector exports to ES `:9200` but Scout's ES is on `:9220`, so no spans arrive | Edit the collector config and restart it (see B4) |
| Scout hangs on start | Old services still running | `node scripts/evals stop`, then retry |
| 429 errors in Lab B | Too many concurrent calls | Lower `--concurrency` |
