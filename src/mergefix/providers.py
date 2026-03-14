"""
LLM providers for mergefix.

Minimal, focused on conflict resolution quality.
"""

from __future__ import annotations

import os
from typing import Protocol

from dotenv import load_dotenv

load_dotenv(
    "/Users/aaronwu/Local/my-projects/give-it-all/.env", override=True
)


class LLMProvider(Protocol):
    def complete(self, system: str, user: str) -> str:
        ...


# ── Claude ────────────────────────────────────────────────────────────────────

class ClaudeProvider:
    def __init__(self, model: str = "claude-haiku-4-5-20251001") -> None:
        import anthropic

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. "
                "Export it or use --provider ollama for free local resolution."
            )
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def complete(self, system: str, user: str) -> str:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text.strip()


# ── OpenAI ────────────────────────────────────────────────────────────────────

class OpenAIProvider:
    def __init__(self, model: str = "gpt-4o-mini") -> None:
        import openai

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def complete(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            max_completion_tokens=4096,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return (resp.choices[0].message.content or "").strip()


# ── Ollama ────────────────────────────────────────────────────────────────────

class OllamaProvider:
    def __init__(self, model: str = "qwen2.5:1.5b") -> None:
        import openai

        self._client = openai.OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama",
        )
        self._model = model

    def complete(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return (resp.choices[0].message.content or "").strip()


# ── Factory ───────────────────────────────────────────────────────────────────

def make_provider(provider: str, model: str | None) -> LLMProvider:
    if provider == "claude":
        return ClaudeProvider(
            model=model or "claude-haiku-4-5-20251001"
        )
    if provider == "openai":
        return OpenAIProvider(model=model or "gpt-4o-mini")
    if provider == "ollama":
        return OllamaProvider(model=model or "qwen2.5:1.5b")
    raise ValueError(f"Unknown provider: {provider!r}")
