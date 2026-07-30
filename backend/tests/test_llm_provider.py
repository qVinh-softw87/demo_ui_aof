from __future__ import annotations

from typing import Any

import httpx
import pytest
from pydantic import BaseModel, ConfigDict

from backend.app.core.config import get_settings
from backend.app.services.llm import (
    _validated_json_content,
    generate_structured,
)


class _ProviderProbe(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    confidence: int


@pytest.mark.parametrize(
    "content",
    [
        '{"answer":"ok","confidence":90}',
        '```json\n{"answer":"ok","confidence":90}\n```',
        'Kết quả: {"answer":"ok","confidence":90}',
    ],
)
def test_ollama_json_validation_accepts_common_response_wrappers(
    content: str,
) -> None:
    parsed = _validated_json_content(_ProviderProbe, content)

    assert parsed.answer == "ok"
    assert parsed.confidence == 90


def test_ollama_provider_posts_schema_grounded_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings()
    original = (
        settings.llm_provider,
        settings.ollama_api_key,
        settings.ollama_model,
        settings.ollama_base_url,
    )
    settings.llm_provider = "ollama"
    settings.ollama_api_key = "test-ollama-key"
    settings.ollama_model = "gpt-oss:120b"
    settings.ollama_base_url = "https://ollama.example/api"
    captured: dict[str, Any] = {}

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {
                "message": {
                    "content": '{"answer":"Ollama","confidence":95}'
                }
            }

    def fake_post(url: str, **kwargs: Any) -> _Response:
        captured["url"] = url
        captured.update(kwargs)
        return _Response()

    monkeypatch.setattr(httpx, "post", fake_post)
    try:
        parsed, generated_by = generate_structured(
            _ProviderProbe,
            system_prompt="Trả lời có cấu trúc.",
            user_content="Nhà cung cấp nào?",
        )
    finally:
        (
            settings.llm_provider,
            settings.ollama_api_key,
            settings.ollama_model,
            settings.ollama_base_url,
        ) = original

    assert parsed is not None
    assert parsed.answer == "Ollama"
    assert generated_by == "OLLAMA_STRUCTURED_OUTPUT"
    assert captured["url"] == "https://ollama.example/api/chat"
    assert captured["headers"]["Authorization"] == "Bearer test-ollama-key"
    assert captured["json"]["model"] == "gpt-oss:120b"
    assert captured["json"]["format"] == "json"
    assert '"confidence"' in captured["json"]["messages"][0]["content"]


def test_ollama_provider_retries_invalid_schema_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings()
    original = (
        settings.llm_provider,
        settings.ollama_api_key,
        settings.ollama_model,
        settings.ollama_base_url,
    )
    settings.llm_provider = "ollama"
    settings.ollama_api_key = "test-ollama-key"
    settings.ollama_model = "gpt-oss:120b"
    settings.ollama_base_url = "https://ollama.example/api"
    responses = iter(
        [
            '{"answer":"thiếu confidence"}',
            '{"answer":"đã sửa","confidence":88}',
        ]
    )
    calls: list[dict[str, Any]] = []

    class _Response:
        def __init__(self, content: str) -> None:
            self.content = content

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"message": {"content": self.content}}

    def fake_post(_: str, **kwargs: Any) -> _Response:
        calls.append(kwargs["json"])
        return _Response(next(responses))

    monkeypatch.setattr(httpx, "post", fake_post)
    try:
        parsed, generated_by = generate_structured(
            _ProviderProbe,
            system_prompt="Trả lời có cấu trúc.",
            user_content="Nhà cung cấp nào?",
        )
    finally:
        (
            settings.llm_provider,
            settings.ollama_api_key,
            settings.ollama_model,
            settings.ollama_base_url,
        ) = original

    assert parsed is not None
    assert parsed.answer == "đã sửa"
    assert generated_by == "OLLAMA_STRUCTURED_OUTPUT"
    assert len(calls) == 2
    assert calls[1]["messages"][-1]["role"] == "user"


def test_ollama_provider_failure_uses_deterministic_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings()
    original = (
        settings.llm_provider,
        settings.ollama_api_key,
        settings.ollama_model,
        settings.ollama_base_url,
    )
    settings.llm_provider = "ollama"
    settings.ollama_api_key = "test-ollama-key"
    settings.ollama_model = "gpt-oss:120b"
    settings.ollama_base_url = "https://ollama.example/api"

    def fail_post(*_: Any, **__: Any) -> None:
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "post", fail_post)
    try:
        parsed, generated_by = generate_structured(
            _ProviderProbe,
            system_prompt="Trả lời có cấu trúc.",
            user_content="Nhà cung cấp nào?",
        )
    finally:
        (
            settings.llm_provider,
            settings.ollama_api_key,
            settings.ollama_model,
            settings.ollama_base_url,
        ) = original

    assert parsed is None
    assert generated_by == "DETERMINISTIC_FALLBACK"
