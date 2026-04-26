"""Anthropic Claude connector — for scripted calls outside Claude Code."""

from __future__ import annotations

from typing import Any

from adforge.config import settings

OPUS = "claude-opus-4-7"
SONNET = "claude-sonnet-4-6"
HAIKU = "claude-haiku-4-5-20251001"
DEFAULT_MODEL = SONNET


def _client():
    from anthropic import Anthropic

    key = settings().anthropic_api_key
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not set. Add to .env or use Claude Code.")
    return Anthropic(api_key=key)


def complete(
    prompt: str,
    *,
    system: str | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 4096,
    temperature: float = 0.2,
    cache_system: bool = True,
) -> str:
    sys_blocks: list[dict[str, Any]] | None = None
    if system:
        sys_blocks = [{"type": "text", "text": system}]
        if cache_system:
            sys_blocks[0]["cache_control"] = {"type": "ephemeral"}

    # Opus 4.7 (and other reasoning-style Claudes) deprecate the `temperature`
    # knob — passing it returns a 400 InvalidRequest. Detect by model id and
    # skip the param entirely. This single bug was masking the entire
    # playable_build → Claude path: every Opus call 400'd, the activity caught
    # the exception, and silently fell back to the deterministic baseline
    # template (the "1-second playable" symptom).
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": sys_blocks if sys_blocks else None,
        "messages": [{"role": "user", "content": prompt}],
    }
    if "opus" not in model.lower():
        kwargs["temperature"] = temperature

    resp = _client().messages.create(**kwargs)
    return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
