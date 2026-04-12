from __future__ import annotations

from fastapi import APIRouter

from app.services.ollama_service import OllamaService

router = APIRouter()


@router.get("")
async def health() -> dict:
    try:
        ollama_status = await OllamaService().health()
    except Exception as exc:
        ollama_status = {"error": str(exc)}
    return {"status": "ok", "ollama": ollama_status}

