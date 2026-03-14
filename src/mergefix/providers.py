"""LLM provider wrappers for mergefix."""

from __future__ import annotations

import os
from typing import Protocol


class LLMProvider(Protocol):
    def resolve(self, prompt: str) -> str: ...


# ── Anthropic ─────────────────────────────────────────────────────────────────

def _anthropic_resolve(prompt: str, model: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


# ── OpenAI ────────────────────────────────────────────────────────────────────

def _openai_resolve(prompt: str, model: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    resp = client.chat.completions.create(
        model=model,
        max_completion_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or ""


# ── Ollama ────────────────────────────────────────────────────────────────────

def _ollama_resolve(prompt: str, model: str) -> str:
    from openai import OpenAI
    client = OpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama",
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or ""


# ── Public factory ────────────────────────────────────────────────────────────

DEFAULT_MODELS = {
    "claude": "claude-haiku-4-5",
    "openai": "gpt-5-nano",
    "ollama": "qwen2.5:1.5b",
}


def resolve_conflict(
    prompt: str,
    provider: str = "claude",
    model: str | None = None,
) -> str:
    """Call the LLM and return raw response text."""
    resolved_model = model or DEFAULT_MODELS.get(provider, DEFAULT_MODELS["claude"])

    if provider == "claude":
        return _anthropic_resolve(prompt, resolved_model)
    elif provider == "openai":
        return _openai_resolve(prompt, resolved_model)
    elif provider == "ollama":
        return _ollama_resolve(prompt, resolved_model)
    else:
        raise ValueError(f"Unknown provider: {provider!r}")
