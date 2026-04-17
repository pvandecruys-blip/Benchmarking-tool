"""
SourceLens — Unified LLM Client
Abstraction layer supporting multiple LLM providers:
- Google Gemini (default, via google-genai SDK)
- OpenAI (GPT-4o, GPT-4o-mini)

Default model: Gemini 3.1 Flash Lite (best cost/performance for structured extraction)
"""

import json
import re
import logging
from typing import Optional
from app.config import get_settings

logger = logging.getLogger(__name__)

# Provider constants
PROVIDER_GEMINI = "gemini"
PROVIDER_OPENAI = "openai"
PROVIDER_ANTHROPIC = "anthropic"

# Model catalog
MODEL_CATALOG = {
    # Anthropic models — PwC GenAI gateway (prefixed routing via Bedrock/Vertex)
    "bedrock.anthropic.claude-sonnet-4-6": {"provider": PROVIDER_ANTHROPIC, "api_name": "bedrock.anthropic.claude-sonnet-4-6", "label": "Claude Sonnet 4.6 (Bedrock)", "cost_tier": "balanced"},
    "bedrock.anthropic.claude-opus-4-6": {"provider": PROVIDER_ANTHROPIC, "api_name": "bedrock.anthropic.claude-opus-4-6", "label": "Claude Opus 4.6 (Bedrock)", "cost_tier": "premium"},
    "bedrock.anthropic.claude-haiku-4-5": {"provider": PROVIDER_ANTHROPIC, "api_name": "bedrock.anthropic.claude-haiku-4-5", "label": "Claude Haiku 4.5 (Bedrock)", "cost_tier": "budget"},
    "vertex_ai.anthropic.claude-sonnet-4-6": {"provider": PROVIDER_ANTHROPIC, "api_name": "vertex_ai.anthropic.claude-sonnet-4-6", "label": "Claude Sonnet 4.6 (Vertex)", "cost_tier": "balanced"},
    # Direct Anthropic names (for standard api.anthropic.com usage)
    "claude-sonnet-4-6": {"provider": PROVIDER_ANTHROPIC, "api_name": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6", "cost_tier": "balanced"},
    "claude-opus-4-7": {"provider": PROVIDER_ANTHROPIC, "api_name": "claude-opus-4-7", "label": "Claude Opus 4.7", "cost_tier": "premium"},
    "claude-haiku-4-5": {"provider": PROVIDER_ANTHROPIC, "api_name": "claude-haiku-4-5", "label": "Claude Haiku 4.5", "cost_tier": "budget"},
    # Gemini models
    "gemini-3.1-flash-lite": {"provider": PROVIDER_GEMINI, "api_name": "gemini-3.1-flash-lite-preview", "label": "Gemini 3.1 Flash Lite", "cost_tier": "budget"},
    "gemini-2.5-flash": {"provider": PROVIDER_GEMINI, "api_name": "gemini-2.5-flash-preview-04-17", "label": "Gemini 2.5 Flash", "cost_tier": "budget"},
    "gemini-2.0-flash": {"provider": PROVIDER_GEMINI, "api_name": "gemini-2.0-flash", "label": "Gemini 2.0 Flash", "cost_tier": "budget"},
    # OpenAI models
    "gpt-4o": {"provider": PROVIDER_OPENAI, "api_name": "gpt-4o", "label": "GPT-4o", "cost_tier": "premium"},
    "gpt-4o-mini": {"provider": PROVIDER_OPENAI, "api_name": "gpt-4o-mini", "label": "GPT-4o Mini", "cost_tier": "budget"},
    "gpt-4.1-mini": {"provider": PROVIDER_OPENAI, "api_name": "gpt-4.1-mini", "label": "GPT-4.1 Mini", "cost_tier": "budget"},
}

DEFAULT_MODEL = "claude-sonnet-4-6"


def get_provider_for_model(model: str) -> str:
    """Determine which provider a model belongs to."""
    if model in MODEL_CATALOG:
        return MODEL_CATALOG[model]["provider"]
    if model.startswith("claude") or "anthropic" in model:
        return PROVIDER_ANTHROPIC
    if model.startswith("gemini"):
        return PROVIDER_GEMINI
    if model.startswith("gpt"):
        return PROVIDER_OPENAI
    return PROVIDER_ANTHROPIC  # default


def get_api_model_name(model: str) -> str:
    """Get the actual API model name string."""
    if model in MODEL_CATALOG:
        return MODEL_CATALOG[model]["api_name"]
    return model


async def llm_generate(
    prompt: str,
    system_prompt: str = "",
    model: str | None = None,
    temperature: float = 0.1,
    max_tokens: int = 4096,
    json_mode: bool = True,
) -> str:
    """
    Unified LLM call supporting multiple providers.
    Returns raw text response.
    """
    settings = get_settings()
    model = model or settings.llm_model or DEFAULT_MODEL
    provider = get_provider_for_model(model)
    api_model = get_api_model_name(model)

    logger.debug(f"LLM call: provider={provider}, model={api_model}")

    if provider == PROVIDER_ANTHROPIC:
        return await _call_anthropic(prompt, system_prompt, api_model, temperature, max_tokens, json_mode)
    elif provider == PROVIDER_GEMINI:
        return await _call_gemini(prompt, system_prompt, api_model, temperature, max_tokens)
    elif provider == PROVIDER_OPENAI:
        return await _call_openai(prompt, system_prompt, api_model, temperature, max_tokens, json_mode)
    else:
        raise ValueError(f"Unknown provider: {provider}")


async def llm_embed(texts: list[str], model: str | None = None) -> list[list[float]]:
    """
    Get embeddings for a list of texts.
    Uses the configured embedding model.
    """
    settings = get_settings()
    embed_model = model or settings.embedding_model

    # Gemini native format: "models/text-embedding-004"
    if embed_model.startswith("models/"):
        return await _embed_gemini(texts, embed_model)
    # Everything else routes through OpenAI-compatible endpoint (works for
    # OpenAI direct, and PwC gateway which serves azure.*/vertex_ai.*/bedrock.*
    # embedding models via OpenAI-compatible protocol).
    return await _embed_openai(texts, embed_model)


# ─── Anthropic Provider ───────────────────────────────────────────────────────

async def _call_anthropic(
    prompt: str,
    system_prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    json_mode: bool,
) -> str:
    """Call Anthropic Claude (via official SDK, optionally through a proxy base_url)."""
    settings = get_settings()

    if not settings.anthropic_api_key:
        logger.warning("No Anthropic API key configured")
        return "[]"

    try:
        from anthropic import AsyncAnthropic

        client_kwargs = {"api_key": settings.anthropic_api_key}
        if settings.anthropic_base_url:
            client_kwargs["base_url"] = settings.anthropic_base_url
        client = AsyncAnthropic(**client_kwargs)

        effective_system = system_prompt
        if json_mode:
            json_instruction = "Respond with valid JSON only. No prose, no markdown code fences."
            effective_system = f"{system_prompt}\n\n{json_instruction}".strip() if system_prompt else json_instruction

        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=effective_system,
            messages=[{"role": "user", "content": prompt}],
        )

        text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
        return text or "[]"

    except Exception as e:
        logger.error(f"Anthropic API call failed: {e}")
        raise


# ─── Gemini Provider ──────────────────────────────────────────────────────────

async def _call_gemini(
    prompt: str,
    system_prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
) -> str:
    """Call Google Gemini via google-genai SDK."""
    settings = get_settings()
    api_key = settings.google_api_key or settings.openai_api_key  # fallback

    if not api_key:
        logger.warning("No Google API key configured")
        return "[]"

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            response_mime_type="application/json",
        )

        if system_prompt:
            config.system_instruction = system_prompt

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )

        return response.text or "[]"

    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        raise


async def _embed_gemini(texts: list[str], model: str) -> list[list[float]]:
    """Get embeddings from Gemini API."""
    settings = get_settings()
    api_key = settings.google_api_key

    if not api_key:
        logger.warning("No Google API key for embeddings — using pseudo-embeddings")
        return [_pseudo_embedding(t) for t in texts]

    try:
        from google import genai

        client = genai.Client(api_key=api_key)

        all_embeddings = []
        # Batch in groups of 100
        for i in range(0, len(texts), 100):
            batch = texts[i:i + 100]
            response = client.models.embed_content(
                model=model,
                contents=batch,
            )
            for emb in response.embeddings:
                all_embeddings.append(emb.values)

        return all_embeddings

    except Exception as e:
        logger.error(f"Gemini embedding failed: {e}")
        return [_pseudo_embedding(t) for t in texts]


# ─── OpenAI Provider ─────────────────────────────────────────────────────────

async def _call_openai(
    prompt: str,
    system_prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    json_mode: bool,
) -> str:
    """Call OpenAI API (or OpenAI-compatible gateway via base_url)."""
    settings = get_settings()

    if not settings.openai_api_key:
        logger.warning("No OpenAI API key configured")
        return "[]"

    try:
        from openai import AsyncOpenAI
        client_kwargs = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            client_kwargs["base_url"] = settings.openai_base_url
        client = AsyncOpenAI(**client_kwargs)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or "[]"

    except Exception as e:
        logger.error(f"OpenAI API call failed: {e}")
        raise


async def _embed_openai(texts: list[str], model: str) -> list[list[float]]:
    """Get embeddings from OpenAI API (or OpenAI-compatible gateway via base_url)."""
    settings = get_settings()

    if not settings.openai_api_key:
        logger.warning("No OpenAI API key — falling back to pseudo-embeddings")
        return [_pseudo_embedding(t) for t in texts]

    try:
        from openai import AsyncOpenAI
        client_kwargs = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            client_kwargs["base_url"] = settings.openai_base_url
        client = AsyncOpenAI(**client_kwargs)

        all_embeddings = []
        for i in range(0, len(texts), 100):
            batch = texts[i:i + 100]
            response = await client.embeddings.create(input=batch, model=model)
            for item in response.data:
                all_embeddings.append(item.embedding)
        return all_embeddings

    except Exception as e:
        logger.error(f"OpenAI embedding failed: {e}")
        return [_pseudo_embedding(t) for t in texts]


# ─── Utilities ────────────────────────────────────────────────────────────────

def parse_json_response(text: str) -> list | dict:
    """Parse JSON from LLM response, handling markdown code blocks."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON: {e}\nResponse: {text[:500]}")
        return []


def _pseudo_embedding(text: str) -> list[float]:
    """Generate a deterministic pseudo-embedding from text hash (for dev mode)."""
    import hashlib
    import struct
    h = hashlib.sha256(text.encode()).digest()
    floats = []
    while len(floats) < 768:
        for i in range(0, min(len(h), 32), 4):
            if len(floats) >= 768:
                break
            val = struct.unpack('f', h[i:i+4])[0]
            floats.append(max(-1.0, min(1.0, val / 1e38)))
        h = hashlib.sha256(h).digest()
    return floats[:768]


def has_api_key() -> bool:
    """Check if any API key is configured."""
    settings = get_settings()
    return bool(settings.anthropic_api_key or settings.google_api_key or settings.openai_api_key)
