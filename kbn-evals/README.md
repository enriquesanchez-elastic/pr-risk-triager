# Lab B: the triager's eval in @kbn/evals

The same eval as the Python lab, written as a Kibana eval suite. It runs inside your Kibana checkout.

1. In Kibana, scaffold a suite named `lab` with the `evals-create-suite` agent skill
   (it writes `kibana.jsonc`, `package.json`, `tsconfig.json`).
2. Copy `playwright.config.ts` and `evals/pr_triage.spec.ts` from this folder into it.
3. Run it (the suite is not registered, so point at its config):

```bash
node scripts/evals start --profile local \
  --config x-pack/platform/packages/shared/kbn-evals-suite-lab/playwright.config.ts \
  --model <connector-a>,<connector-b> --judge <judge-connector>
```

Connector ids come from `node scripts/evals init`. Check your setup first with
`node scripts/evals start --suite smoke-tests --profile local`.
