# Lab B: the same eval in @kbn/evals

**This is a reduced version of the Lab A use case, not the same experiment.** It has 3 cases instead of 10, a different prompt, plain JSON parsing instead of structured output, no fallback check, and different evaluators, so Lab A and Lab B scores are not comparable. Also, "2 passed" means the two Playwright tests (one per model) ran to the end. The spec records scores and asserts no minimum, so it says nothing about quality. With 3 examples the comparison page shows you how the UI works; it is too little data to choose a model, and "no significant difference" there means not enough evidence, not that the models are equal.

Verified on upstream Kibana `main`, November 2026, in a clean `git worktree`: bootstrap, scaffold, B3 against `eis-google-gemini-3-0-flash` and `eis-openai-gpt-5-2` with `eis-anthropic-claude-4-6-sonnet` as judge (2 passed, about 3.6 min), and `node scripts/evals compare`. The `inputTokens`/`outputTokens` evaluators only produce scores once the EDOT collector exports to Scout's Elasticsearch (see B4); the UI half of B4 was not opened. Facilitators: run B1 yourself before the session.

## Before you start

You need a Kibana checkout, bootstrapped, before the session. Use a clean worktree on upstream `main`. Run the first command inside an existing Kibana clone whose `origin` is `elastic/kibana`:

```bash
git worktree add ../kibana-clean origin/main --detach
cd ../kibana-clean
corepack enable && corepack prepare pnpm@12.4.2 --activate   # first time only
pnpm kbn bootstrap
node scripts/evals doctor
```

This repo (`git checkout lab-b`) supplies the two files you copy in: `kbn-evals/playwright.config.ts` and `kbn-evals/evals/pr_triage.spec.ts`. It needs `vault login --method oidc` for the EIS models.

You finish Lab B with the triage eval running as a Kibana suite: three PRs, three code evaluators, the criteria judge and token counts, stored as an experiment in the evals UI. The spec is in the repo at `kbn-evals/evals/pr_triage.spec.ts`. Commands run from the Kibana repo root.

Lab B calls models through Kibana connectors, not the LLM gateway, so `els` is not involved.

### B1. Validate your setup (2 min)

```bash
node scripts/evals start --suite smoke-tests --profile local
```

The first run asks for connectors, starts Scout and the EDOT collector, and runs the smoke suite; later runs reuse the services. If it fails, run `node scripts/evals doctor`.

### B2. Add the spec and read it (2 min)

Scaffold a suite named `lab` with the `evals-create-suite` agent skill. It creates `x-pack/platform/packages/shared/kbn-evals-suite-lab/` with `kibana.jsonc`, `package.json` and `tsconfig.json`. Then copy `kbn-evals/playwright.config.ts` and `kbn-evals/evals/pr_triage.spec.ts` from your clone of this repo (branch `lab-b`) into that package, keeping the `evals/` folder for the spec. Match the spec to the anatomy:

1. **Dataset**: three PRs. The expected risk sits in each example's `output`; `mustCover` sits in `metadata`, because the criteria judge reads input, output and metadata.
2. **Task**: one `inferenceClient.chatComplete` call, bound to the model of the current Playwright project, asking for JSON.
3. **Evaluators**: `ValidJson`, `RiskMatches` and `NoUnderestimate` (CODE, each with `direction: 'maximize'`), `evaluators.criteria([...])` named `FocusCoverage`, and the trace-based `inputTokens` and `outputTokens`.

### Before B3: point the results at Scout

`--profile local` exports results to the Elasticsearch and Kibana URLs in `x-pack/platform/packages/shared/kbn-evals/scripts/vault/config.local.json`, which default to `localhost:9200` and `localhost:5601`: a separate dev stack (`pnpm es snapshot` and `pnpm start`). The Scout stack that `evals start` launches listens elsewhere (ES `:9220`, Kibana `:5620`). Either run the dev stack, or point everything at Scout's ports:
- In `config.local.json`: the two Elasticsearch URLs to `:9220`, and the Kibana URL to `:5620` (no `/dev` base path).
- In the EDOT collector config, `data/edot_collector/otel-collector-config.yml` (generated and gitignored): change `endpoint: http://host.docker.internal:9200` to `:9220`, then `docker restart kibana-edot-collector`. The collector hardcodes `:9200`; without this change every span export fails with `connection refused`, `trace.id` never exists, and `inputTokens`/`outputTokens` score null (the Tokens column shows `-`).

B4 reads the results from the Kibana you set up here.

### B3. Run it against two models (2 min)

```bash
node scripts/evals start --profile local \
  --config x-pack/platform/packages/shared/kbn-evals-suite-lab/playwright.config.ts \
  --model <connector-a>,<connector-b> --judge <judge-connector>
```

The suite isn't registered in `evals.suites.json`, so `--config` points at it directly. Connector ids come from `node scripts/evals init`. Pick a judge from a different family than both models.

Gotchas:
- Each `--model` must also be a Playwright project of the suite, and that list can lag the live connectors. If you see `Project(s) "<id>" not found`, the error lists the valid ids: pick one of those (for example `eis-google-gemini-3-0-flash`, not `eis-google-gemini-3-7-flash`).
- Without a TTY (scripts, CI, an agent) the connector prompt can't appear. Pass `--evaluation-connector-id <judge-connector>` and `--model` explicitly. `node scripts/evals start` prints the re-run command with the ids it used.

### B4. Compare in the UI (1 min)

In the Kibana your profile exports to (set up before B3), open `/app/management/ai/evals` → Experiments, select the two runs and use **Compare selected** (a paired statistical comparison per evaluator; the test depends on the score type), or run `EVAL_KBN_URL=<kibana-url> node scripts/evals compare <exp-1> <exp-2>` (the experiment ids are printed at the end of each run; `compare` has no `--profile` flag and reads `EVAL_KBN_URL`, for Scout use `http://elastic:changeme@localhost:5620`). The Tracing tab shows the spans the token evaluators read.
