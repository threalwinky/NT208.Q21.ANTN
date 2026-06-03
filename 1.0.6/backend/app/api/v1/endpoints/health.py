from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from redis import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.embeddings import get_embedding_provider
from app.services.llm import get_llm_provider
from app.services.qdrant_service import QdrantService

router = APIRouter()


def _status_ok(data: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, **data}


def _status_error(exc: Exception) -> dict[str, Any]:
    return {"ok": False, "error": str(exc)}


@router.get("")
async def health() -> dict[str, Any]:
    settings = get_settings()
    checks: dict[str, str] = {}

    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
        checks["db"] = "ok"
    except Exception as exc:
        checks["db"] = f"error: {exc}"

    try:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    try:
        QdrantService().client.get_collections()
        checks["qdrant"] = "ok"
    except Exception as exc:
        checks["qdrant"] = f"error: {exc}"

    status = "ok" if all(value == "ok" for value in checks.values()) else "degraded"
    return {
        "status": status,
        "checks": checks,
        "app": settings.app_name,
        "version": settings.app_version,
        "llm_provider": settings.llm_provider,
    }


@router.get("/dependencies")
async def dependencies() -> dict[str, Any]:
    settings = get_settings()
    checks: dict[str, Any] = {}

    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
        checks["postgres"] = _status_ok({"driver": settings.database_url.split(":", 1)[0]})
    except Exception as exc:
        checks["postgres"] = _status_error(exc)

    try:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        checks["redis"] = _status_ok({"ping": redis.ping()})
    except Exception as exc:
        checks["redis"] = _status_error(exc)

    try:
        collections = QdrantService().client.get_collections()
        checks["qdrant"] = _status_ok({"collections": [item.name for item in collections.collections]})
    except Exception as exc:
        checks["qdrant"] = _status_error(exc)

    try:
        checks["llm_provider"] = _status_ok(await get_llm_provider().health())
    except Exception as exc:
        checks["llm_provider"] = _status_error(exc)

    try:
        checks["embedding_provider"] = _status_ok(await get_embedding_provider().health())
    except Exception as exc:
        checks["embedding_provider"] = _status_error(exc)

    checks["spotify_config"] = {
        "ok": (not settings.spotify_is_enabled) or bool(settings.spotify_client_id and settings.spotify_client_secret),
        "enabled": settings.spotify_is_enabled,
    }
    status = "ok" if all(item.get("ok") for item in checks.values()) else "degraded"
    return {"status": status, "dependencies": checks}
