from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


_PLACEHOLDER_VALUES = {
    "",
    "secret",
    "changeme",
    "studify123",
    "replace_me",
    "replace-this-with-a-long-random-secret",
}


class Settings(BaseSettings):
    app_name: str = "Studify"
    app_env: str = "development"
    app_version: str = "1.0.5"
    api_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg2://studify:studify_local_dev@localhost:5432/studify"
    # Connection pooling – tránh connection exhaustion dưới tải cao
    db_pool_size: int = 10
    db_max_overflow: int = 5
    db_pool_recycle: int = 1800
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"

    llm_provider: str = "mimo"
    # OpenAI-compatible endpoint (giữ để backward compat)
    mimo_base_url: str = "https://token-plan-ams.xiaomimimo.com/v1"
    # Anthropic-compatible endpoint (dùng trong v1.0.5+)
    mimo_anthropic_base_url: str = "https://token-plan-ams.xiaomimimo.com/anthropic/v1"
    mimo_api_key: str = ""
    mimo_chat_model: str = "mimo-v2.5-pro"
    mimo_temperature: float = 0.2
    mimo_top_p: float = 0.9
    mimo_max_completion_tokens: int = 1200
    mimo_timeout_seconds: int = 120

    embedding_provider: str = "ollama"
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_fallback_urls: str = ""
    ollama_chat_model: str = "minimax-m2.7:cloud"
    ollama_embed_model: str = "nomic-embed-text"

    jwt_secret: str = "replace-this-with-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    cors_origins: str = "http://localhost:3000"

    crawler_user_agent: str = "StudifyBot/1.0.5 (+https://uit.edu.vn)"
    crawler_timeout_seconds: int = 25
    crawler_delay_seconds: float = 1.0
    crawler_max_pages: int = 20
    crawler_retries: int = 2
    data_dir: str = "/app/data"
    knowledge_refresh_poll_seconds: int = 300

    enable_admin_demo: bool = True
    enable_document_upload: bool = True
    enable_email_reminders: bool = False
    enable_evaluation_runner: bool = True
    # Streaming bật mặc định từ v1.0.5 (Anthropic SSE realtime)
    enable_mimo_streaming: bool = True
    enable_wellbeing: bool = True
    enable_spotify: bool = False
    enable_ai_note_reflection: bool = False
    # Web search tool – tìm kiếm internet khi RAG không đủ thông tin
    enable_web_search: bool = True
    web_search_max_results: int = 5

    spotify_access_token: str = ""
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = "http://localhost:8000/api/v1/integrations/spotify/callback"
    spotify_token_encryption_key: str = ""
    spotify_enabled: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def spotify_is_enabled(self) -> bool:
        return self.enable_spotify or self.spotify_enabled


def _is_placeholder(value: str) -> bool:
    return value.strip().lower() in _PLACEHOLDER_VALUES


def validate_runtime_config(settings: Settings | None = None) -> None:
    current = settings or get_settings()
    if current.llm_provider not in {"mimo", "ollama"}:
        raise RuntimeError("LLM_PROVIDER chỉ hỗ trợ mimo hoặc ollama.")
    if current.embedding_provider != "ollama":
        raise RuntimeError("EMBEDDING_PROVIDER hiện chỉ hỗ trợ ollama.")
    if current.llm_provider == "mimo" and _is_placeholder(current.mimo_api_key) and current.is_production:
        raise RuntimeError("MIMO_API_KEY bắt buộc khi APP_ENV=production và LLM_PROVIDER=mimo.")
    if current.spotify_is_enabled and current.is_production:
        if _is_placeholder(current.spotify_client_id) or _is_placeholder(current.spotify_client_secret):
            raise RuntimeError("Spotify được bật nhưng SPOTIFY_CLIENT_ID/SPOTIFY_CLIENT_SECRET chưa hợp lệ.")
    if not current.is_production:
        return
    if _is_placeholder(current.jwt_secret):
        raise RuntimeError("JWT_SECRET chưa an toàn cho production.")
    if "studify123" in current.database_url.lower():
        raise RuntimeError("DATABASE_URL còn dùng mật khẩu mặc định studify123.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
