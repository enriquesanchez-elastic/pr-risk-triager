"""Reach models through Elastic's LLM gateway (AgentRouter). No API keys.

The gateway is OpenAI-compatible. People authenticate with a short-lived Okta token
printed by the `els` CLI (`els auth login --env <env>`); els caches it and only opens
the browser again when it expires.

    ELS_ENV          dev | test | prod (default prod, like els)
    LLM_GATEWAY_URL  override the base URL (e.g. a local mock)
    ELS_BIN          path to els, if it is not on PATH
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from functools import cache

from openai import AsyncOpenAI
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel
from pydantic_ai.profiles.openai import OpenAIModelProfile
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

BASE_URLS = {
    "dev": "https://llm.dev.elastichosting.ai/v1",
    "test": "https://llm.uat.elastichosting.ai/v1",
    "prod": "https://llm.idea.elastichosting.ai/v1",
}
DEFAULT_ENV = "prod"
# Claude needs max_tokens on every request; Gemini and GPT reason first, so leave room.
MAX_TOKENS = 4000


def gateway_env() -> str:
    env = os.environ.get("ELS_ENV", DEFAULT_ENV)
    if env not in BASE_URLS:
        raise ValueError(f"ELS_ENV must be one of {sorted(BASE_URLS)}, got {env!r}")
    return env


def els_token(env: str | None = None) -> str:
    """A fresh Okta access token for the gateway, from the els CLI."""
    els = os.environ.get("ELS_BIN", "els")
    return subprocess.check_output([els, "auth", "login", "--env", env or gateway_env()], text=True).strip()


@cache
def _provider(env: str) -> OpenAIProvider:
    async def token() -> str:  # called before every request, so expiry is handled
        return await asyncio.to_thread(els_token, env)

    base_url = os.environ.get("LLM_GATEWAY_URL", BASE_URLS[env])
    # max_retries=0: never replay a request that may already have been billed.
    return OpenAIProvider(openai_client=AsyncOpenAI(base_url=base_url, api_key=token, max_retries=0))


def gateway_model(name: str, env: str | None = None) -> Model:
    """A pydantic-ai model for a gateway model name, e.g. gemini-3.7-flash or claude-sonnet-4-6."""
    provider = _provider(env or gateway_env())
    settings = ModelSettings(max_tokens=MAX_TOKENS)
    if name.startswith("gpt"):
        # GPT models are served on /v1/responses only.
        return OpenAIResponsesModel(name, provider=provider, settings=settings)
    # Gemini, Claude, Kimi, Mistral: /v1/chat/completions with max_tokens (not max_completion_tokens).
    return OpenAIChatModel(
        name,
        provider=provider,
        settings=settings,
        profile=OpenAIModelProfile(
            openai_chat_supports_max_completion_tokens=False,
            # Claude on Vertex rejects strict tool schemas: the gateway turns them into
            # structured_outputs, which an org policy blocks. Plain tool calls work everywhere.
            openai_supports_strict_tool_definition=False,
            default_structured_output_mode="tool",
        ),
    )
