from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Studify"
    app_env: str = "development"
    api_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg2://studify:studify123@localhost:5432/studify"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"

    ollama_base_url: str = "http://host.docker.internal:11435"
    ollama_chat_model: str = "minimax-m2.7:cloud"
    ollama_embed_model: str = "nomic-embed-text"

    jwt_secret: str = "replace-this-with-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    cors_origins: str = "http://localhost:3000"

    crawler_user_agent: str = "StudifyBot/1.0 (+https://uit.edu.vn)"
    crawler_timeout_seconds: int = 25
    crawler_delay_seconds: float = 1.0
    crawler_max_pages: int = 20
    crawler_retries: int = 2
    data_dir: str = "/app/data"
    knowledge_refresh_poll_seconds: int = 300
    spotify_access_token: str = ""
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_enabled: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
