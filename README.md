# pr-risk-triager

A small AI tool for the evals workshop. Give it a pull request; it answers two questions a QA engineer asks first:

- **How risky is this change?** `low`, `medium` or `high`
- **What should we test first?** up to 5 focus areas, most important first

One LLM call through [pydantic-ai](https://ai.pydantic.dev), structured output, no agents or tools.

## Try it

```bash
uv sync
export OPENAI_API_KEY=...            # or ANTHROPIC_API_KEY with --model anthropic:claude-sonnet-4-5
uv run triage examples/pr_pagination.json
uv run pytest                        # unit tests, no model needed
```

The model defaults to `openai:gpt-5.2`; override with `--model` or `TRIAGER_MODEL`.

## Status

The unit tests pass and CI is green. Nobody knows whether the triage is any good.
That is what the workshop fixes: this repo has **no evals yet**.

The finished evals live on the `solution` branch.
