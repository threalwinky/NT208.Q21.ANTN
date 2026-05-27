from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.services.llm.base import LLMProvider
from app.services.llm.mimo_provider import MimoProvider
from app.services.llm.ollama_provider import OllamaProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    provider = settings.llm_provider.lower().strip()
    if provider == "mimo":
        return MimoProvider()
    if provider == "ollama":
        return OllamaProvider()
    raise RuntimeError("LLM_PROVIDER chỉ hỗ trợ mimo hoặc ollama.")
