"""
LLM abstraction layer.

This is the ONLY module in the codebase that talks to an external LLM API.
Every agent calls `generate_text()` or `generate_json()` from here instead
of importing anthropic/openai directly. That means:

  - Swapping providers = change one env var, not application code.
  - Running with NO key at all = `llm_enabled` is False, and callers must
    always provide a deterministic fallback (see agents/*.py — each agent
    computes a rule-based result FIRST, then optionally asks the LLM to
    phrase/augment it).
  - No agent ever "fails" if the key is missing or the API errors out;
    it just silently stays in deterministic mode and the caller marks the
    output as `llm_enhanced: False` so the UI/report is honest about it.
"""
from __future__ import annotations
import json
import logging
from typing import Any, Optional

from app.core.config import get_settings

logger = logging.getLogger("procuremind.llm")

settings = get_settings()


class LLMUnavailable(Exception):
    """Raised internally when no provider is configured; callers should catch and fall back."""


def _call_anthropic(prompt: str, system: str, max_tokens: int) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    resp = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    parts = [b.text for b in resp.content if getattr(b, "type", "") == "text"]
    return "\n".join(parts)


def _call_openai(prompt: str, system: str, max_tokens: int) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    resp = client.chat.completions.create(
        model=settings.openai_model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content or ""


def generate_text(prompt: str, system: str = "", max_tokens: int = 800) -> Optional[str]:
    """Returns LLM text, or None if no provider is configured / call failed."""
    if not settings.llm_enabled:
        return None
    try:
        if settings.llm_provider == "anthropic":
            return _call_anthropic(prompt, system, max_tokens)
        if settings.llm_provider == "openai":
            return _call_openai(prompt, system, max_tokens)
    except Exception as exc:  # noqa: BLE001 - we deliberately never crash the request
        logger.warning("LLM call failed (%s); falling back to deterministic output: %s",
                        settings.llm_provider, exc)
        return None
    return None


def generate_json(prompt: str, system: str = "", max_tokens: int = 1000) -> Optional[dict[str, Any]]:
    """Same as generate_text but parses the result as JSON. Returns None on any failure."""
    sys_prompt = (system + "\n\n" if system else "") + (
        "Respond with ONLY valid JSON. No markdown fences, no preamble, no commentary."
    )
    raw = generate_text(prompt, system=sys_prompt, max_tokens=max_tokens)
    if raw is None:
        return None
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("LLM returned non-JSON output; discarding and falling back.")
        return None


def llm_status() -> dict[str, Any]:
    return {
        "provider": settings.llm_provider,
        "enabled": settings.llm_enabled,
        "mode": "llm-augmented" if settings.llm_enabled else "deterministic (rule-based)",
    }
