# pr-risk-triager

A small AI tool for the evals workshop. Give it a pull request; it answers two questions a QA engineer asks first:

- **How risky is this change?** `low`, `medium` or `high`
- **What should we test first?** up to 5 focus areas, most important first

One LLM call through [pydantic-ai](https://ai.pydantic.dev) and Elastic's LLM gateway (AgentRouter), structured output, no agents or tools.

## Try it

The gateway uses your Okta login through the `els` CLI. There are no API keys.
You need to be in exactly one `AgentRouter - <tier>` Okta group.

```bash
els auth login --env prod            # once: opens the browser for Okta, then els caches the token
uv sync
uv run triage examples/pr_pagination.json
uv run pytest                        # unit tests, no gateway needed
```

| Setting | Default | What it does |
| --- | --- | --- |
| `--model` / `TRIAGER_MODEL` | `gemini-3.7-flash` | Any model the gateway serves, e.g. `claude-sonnet-4-6`, `gpt-5.4` |
| `ELS_ENV` | `prod` | Gateway environment: `dev`, `test` or `prod` (test allows 27,500 tokens per hour) |
| `ELS_BIN` | `els` | Path to els if it isn't on your PATH |

GPT models go through the gateway's Responses API, everything else through chat completions;
`src/triager/gateway.py` handles both.

## Status

The unit tests pass and CI is green. Nobody knows whether the triage is any good.
That is what the workshop fixes: this repo has **no evals yet**.

**Running the session? Follow [GUIDE.md](GUIDE.md).**

The finished Python evals live on the `solution` branch. `kbn-evals/` holds the same eval for @kbn/evals (Lab B).
