"""Mistral connector — cheap text classification + JSON extraction.

We use Mistral models for the high-volume per-creative pattern labeling step in
creative_forge — cheaper and faster than Opus/Gemini-Pro for short JSON tasks.
"""

from __future__ import annotations

import json
from typing import Any

from adforge.config import settings
from adforge.utils import strip_json_fences

DEFAULT_MODEL = "mistral-large-latest"
SMALL_MODEL = "mistral-small-latest"


def _client():
    from mistralai import Mistral

    key = settings().mistral_api_key
    if not key:
        raise RuntimeError("MISTRAL_API_KEY not set. Add it to .env to use Mistral.")
    return Mistral(api_key=key)


def complete(
    prompt: str,
    *,
    system: str | None = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
    max_tokens: int = 1024,
    json_mode: bool = False,
) -> str:
    msgs: list[dict[str, Any]] = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": msgs,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    resp = _client().chat.complete(**kwargs)
    return resp.choices[0].message.content or ""


def complete_json(prompt: str, *, system: str | None = None, model: str = DEFAULT_MODEL) -> dict:
    raw = complete(prompt, system=system, model=model, json_mode=True)
    return json.loads(strip_json_fences(raw))
