"""
SourceLens — Configuration Routes
API key management, model selection, and settings endpoints.
Supports multiple LLM providers (Gemini, OpenAI).
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.config import get_settings, update_settings
from app.services.llm_client import MODEL_CATALOG, has_api_key

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigUpdateRequest(BaseModel):
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None
    verification_strictness: Optional[str] = None
    chunk_size: Optional[int] = None
    max_chunks_per_query: Optional[int] = None
    demo_mode: Optional[bool] = None


class ApiKeyTestRequest(BaseModel):
    api_key: str
    provider: str = "gemini"  # "gemini" or "openai"


@router.get("")
async def get_config():
    """Get current configuration (excluding sensitive values)."""
    settings = get_settings()
    return {
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "embedding_model": settings.embedding_model,
        "verification_strictness": settings.verification_strictness,
        "chunk_size": settings.chunk_size,
        "max_chunks_per_query": settings.max_chunks_per_query,
        "has_api_key": has_api_key(),
        "has_google_key": bool(settings.google_api_key),
        "has_openai_key": bool(settings.openai_api_key),
        "demo_mode": settings.demo_mode,
        "available_models": {
            k: {"label": v["label"], "provider": v["provider"], "cost_tier": v["cost_tier"]}
            for k, v in MODEL_CATALOG.items()
        },
    }


@router.put("")
async def update_config(req: ConfigUpdateRequest):
    """Update configuration settings."""
    updates = {}
    if req.openai_api_key is not None:
        updates["openai_api_key"] = req.openai_api_key
    if req.google_api_key is not None:
        updates["google_api_key"] = req.google_api_key
    if req.llm_model is not None:
        updates["llm_model"] = req.llm_model
    if req.embedding_model is not None:
        updates["embedding_model"] = req.embedding_model
    if req.verification_strictness is not None:
        updates["verification_strictness"] = req.verification_strictness
    if req.chunk_size is not None:
        updates["chunk_size"] = req.chunk_size
    if req.max_chunks_per_query is not None:
        updates["max_chunks_per_query"] = req.max_chunks_per_query
    if req.demo_mode is not None:
        updates["demo_mode"] = req.demo_mode

    settings = update_settings(**updates)
    return {
        "status": "updated",
        "has_api_key": has_api_key(),
        "has_google_key": bool(settings.google_api_key),
        "has_openai_key": bool(settings.openai_api_key),
        "llm_model": settings.llm_model,
        "demo_mode": settings.demo_mode,
    }


@router.post("/test-api-key")
async def test_api_key(req: ApiKeyTestRequest):
    """Validate an API key for the specified provider."""
    if not req.api_key:
        return {"valid": False, "error": "No API key provided"}

    if req.provider == "gemini":
        try:
            from google import genai
            client = genai.Client(api_key=req.api_key)
            # Quick test — list models
            models = client.models.list()
            return {"valid": True, "provider": "gemini"}
        except Exception as e:
            return {"valid": False, "error": str(e), "provider": "gemini"}

    elif req.provider == "openai":
        try:
            from openai import OpenAI
            client = OpenAI(api_key=req.api_key)
            client.models.list()
            return {"valid": True, "provider": "openai"}
        except Exception as e:
            return {"valid": False, "error": str(e), "provider": "openai"}

    return {"valid": False, "error": f"Unknown provider: {req.provider}"}
