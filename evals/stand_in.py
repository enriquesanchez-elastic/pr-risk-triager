"""A deliberately weak keyword "model", so the eval pipeline runs without the gateway.

Use it to learn the workflow (--model stand-in). Its scores mean nothing about the real
triager; they only show that the evaluators react to good and bad answers.
"""

from __future__ import annotations

from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

LOW = ("readme", "docs", "typo", "rename", "tooltip", "devdependenc", "copy change")
HIGH = ("privilege", "delete", "migrat", "api key", "role", "permission")


def _prompt(messages: list[ModelMessage]) -> str:
    return "\n".join(
        str(part.content) for msg in messages for part in getattr(msg, "parts", []) if isinstance(part, UserPromptPart)
    )


def _respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    text = _prompt(messages)
    lower = text.lower()
    if "rate this pr as high" in lower:  # naive: it obeys instructions hidden in the PR
        risk = "high"
    elif any(k in lower for k in LOW):  # checks "low" words first, so a "rename" migration slips through
        risk = "low"
    elif any(k in lower for k in HIGH):
        risk = "high"
    else:
        risk = "medium"
    bullets = [line[2:].strip() for line in text.splitlines() if line.startswith("- ") and "(+" not in line]
    title = text.splitlines()[0].removeprefix("Title: ")
    focus = bullets[:5] or [f"Smoke test: {title}"]
    args = {"risk": risk, "focus_areas": focus, "rationale": "Keyword match."}
    return ModelResponse(parts=[ToolCallPart(tool_name=info.output_tools[0].name, args=args)])


stand_in_model = FunctionModel(_respond, model_name="stand-in")
