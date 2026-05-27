from __future__ import annotations

import pytest

from app.services.llm.mimo_provider import MimoProvider


def test_mimo_payload_matches_openai_compatible_contract() -> None:
    provider = MimoProvider()
    provider.settings.mimo_chat_model = "mimo-v2.5-pro"
    provider.settings.mimo_temperature = 0.2
    provider.settings.mimo_top_p = 0.9
    provider.settings.mimo_max_completion_tokens = 256

    payload = provider._payload([{"role": "user", "content": "ping"}], stream=False)

    assert payload["model"] == "mimo-v2.5-pro"
    assert payload["messages"][0]["content"] == "ping"
    assert payload["max_completion_tokens"] == 256
    assert payload["temperature"] == 0.2
    assert payload["top_p"] == 0.9
    assert payload["stream"] is False


def test_mimo_uses_api_key_header() -> None:
    provider = MimoProvider()
    provider.settings.mimo_api_key = "unit-test-key"

    headers = provider._headers()

    assert headers["api-key"] == "unit-test-key"
    assert "Authorization" not in headers


def test_mimo_requires_configured_api_key() -> None:
    provider = MimoProvider()
    provider.settings.mimo_api_key = ""

    with pytest.raises(RuntimeError):
        provider._headers()
