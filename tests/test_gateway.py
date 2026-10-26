"""The gateway wiring, checked against a local mock of the gateway: no network, no Okta."""

import json
import os
import stat
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel

from triager import PullRequest, triage
from triager import gateway
from triager.triage import FALLBACK

CALLS: list[dict] = []


class MockGateway(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        CALLS.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
        tool = body["tools"][0]["function"]["name"]
        args = {"risk": "high", "focus_areas": ["Users without alerts:all get a 403"], "rationale": "Deletes data."}
        reply = {
            "id": "chatcmpl-1", "object": "chat.completion", "created": 0, "model": body["model"],
            "choices": [{"index": 0, "finish_reason": "tool_calls", "message": {
                "role": "assistant", "content": None,
                "tool_calls": [{"id": "call_1", "type": "function",
                                "function": {"name": tool, "arguments": json.dumps(args)}}]}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        data = json.dumps(reply).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture
def mock_gateway(tmp_path, monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), MockGateway)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    els = tmp_path / "els"
    els.write_text('#!/bin/sh\necho "okta-token-for-$4"\n')  # els auth login --env <env>
    els.chmod(els.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("LLM_GATEWAY_URL", f"http://127.0.0.1:{server.server_port}/v1")
    monkeypatch.setenv("ELS_BIN", str(els))
    monkeypatch.setenv("ELS_ENV", "dev")
    CALLS.clear()
    yield
    server.shutdown()


def test_gpt_models_use_the_responses_api_and_others_chat_completions():
    assert isinstance(gateway.gateway_model("gpt-5.4", env="dev"), OpenAIResponsesModel)
    assert isinstance(gateway.gateway_model("gemini-3.7-flash", env="dev"), OpenAIChatModel)
    assert isinstance(gateway.gateway_model("claude-sonnet-4-6", env="dev"), OpenAIChatModel)


def test_unknown_environment_is_rejected(monkeypatch):
    monkeypatch.setenv("ELS_ENV", "staging")
    with pytest.raises(ValueError):
        gateway.gateway_env()


def test_triage_calls_the_gateway_with_an_els_token(mock_gateway):
    pr = PullRequest(title="Add 'Delete all closed alerts' bulk action")
    result = triage(pr, model="claude-sonnet-4-6")
    assert result.risk == "high"
    call = CALLS[0]
    assert call["path"] == "/v1/chat/completions"
    assert call["auth"] == "Bearer okta-token-for-dev"
    assert call["body"]["model"] == "claude-sonnet-4-6"
    assert call["body"]["max_tokens"] == gateway.MAX_TOKENS  # Claude rejects requests without it
    assert "max_completion_tokens" not in call["body"]


def test_not_signed_in_falls_back(mock_gateway, monkeypatch):
    monkeypatch.setenv("ELS_BIN", "false")  # els fails: no token
    assert triage(PullRequest(title="t"), model="gemini-3.7-flash") == FALLBACK
    assert CALLS == []
