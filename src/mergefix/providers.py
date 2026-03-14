"""
LLM providers and prompt building for mergefix.
"""

from __future__ import annotations

import os
from typing import Optional


CLAUDE_DEFAULT_MODEL = "claude-haiku-4-5-20251001"
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"
OLLAMA_DEFAULT_MODEL = "qwen2.5:1.5b"
OLLAMA_BASE_URL = "http://localhost:11434/v1"

DEFAULT_MODELS = {
    "claude": CLAUDE_DEFAULT_MODEL,
    "openai": OPENAI_DEFAULT_MODEL,
    "ollama": OLLAMA_DEFAULT_MODEL,
}


def detect_language(file_path: str) -> str:
    """Return a language-specific hint string based on file extension."""
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    hints = {
        "py": "\nPython-specific: prefer explicit imports, avoid mutable defaults, maintain consistent indentation.",
        "js": "\nJavaScript-specific: prefer const/let over var, handle async/await carefully, deduplicate imports.",
        "ts": "\nTypeScript-specific: preserve type annotations and interfaces from both sides when possible.",
        "go": "\nGo-specific: handle error returns properly, preserve all error checks, avoid goroutine leaks.",
        "rs": "\nRust-specific: handle ownership and lifetimes correctly, preserve error propagation with ?.",
        "java": "\nJava-specific: preserve annotations, deduplicate imports at top of file.",
        "rb": "\nRuby-specific: follow Ruby idioms, prefer blocks and iterators.",
        "cs": "\nC#-specific: preserve nullable annotations and async/await patterns.",
    }
    return hints.get(ext, "")


def build_resolution_prompt(
    file_path: str,
    ours_label: str,
    theirs_label: str,
    ours: str,
    base: Optional[str],
    theirs: str,
    context_before: str,
    context_after: str,
    language_hint: str = "",
) -> tuple[str, str]:
    """Build (system_prompt, user_prompt) for resolving a conflict."""
    system = (
        "You are an expert software engineer resolving a git merge conflict.\n"
        "Your job is to produce the single best resolution that:\n"
        "1. Preserves the intent of BOTH sides when possible\n"
        "2. Eliminates duplicate logic, redundant imports, or repeated code\n"
        "3. Follows the code style of the surrounding context\n"
        "4. Does NOT add conflict markers or merge comments\n\n"
        "Output ONLY the resolved code — no explanation, no markdown fences, "
        "no conflict markers. The output replaces the entire conflict block."
        f"{language_hint}"
    )

    context_section = ""
    if context_before.strip():
        context_section += f"<context_before>\n{context_before.rstrip()}\n</context_before>\n\n"

    base_section = ""
    if base:
        base_section = f"<base_original>\n{base.rstrip()}\n</base_original>\n\n"

    after_section = ""
    if context_after.strip():
        after_section = f"<context_after>\n{context_after.rstrip()}\n</context_after>\n\n"

    user = (
        f"File: {file_path}\n\n"
        f"{context_section}"
        f"<conflict>\n"
        f"<<<<<<< {ours_label}\n"
        f"{ours.rstrip()}\n"
        f"{base_section}"
        f"=======\n"
        f"{theirs.rstrip()}\n"
        f">>>>>>> {theirs_label}\n"
        f"</conflict>\n\n"
        f"{after_section}"
        f"Resolve this conflict. Output only the resolved code."
    )
    return system, user


def call_llm(
    system: str,
    user: str,
    provider: str = "claude",
    model: Optional[str] = None,
) -> str:
    """Call the LLM with system+user prompts, return text response."""
    resolved_model = model or DEFAULT_MODELS.get(provider, CLAUDE_DEFAULT_MODEL)
    if provider == "claude":
        return _call_claude(system, user, resolved_model)
    elif provider == "openai":
        return _call_openai(system, user, resolved_model)
    elif provider == "ollama":
        return _call_openai(
            system, user, resolved_model,
            base_url=OLLAMA_BASE_URL,
            api_key="ollama",
        )
    else:
        raise ValueError(f"Unknown provider: {provider!r}. Use claude, openai, or ollama.")


def resolve_conflict(
    prompt: str,
    provider: str = "claude",
    model: Optional[str] = None,
) -> str:
    """Call LLM with a pre-built prompt string. Returns raw text."""
    resolved_model = model or DEFAULT_MODELS.get(provider, CLAUDE_DEFAULT_MODEL)
    if provider == "claude":
        return _call_claude("", prompt, resolved_model, single_msg=True)
    elif provider == "openai":
        return _call_openai("", prompt, resolved_model, single_msg=True)
    elif provider == "ollama":
        return _call_openai(
            "", prompt, resolved_model,
            base_url=OLLAMA_BASE_URL, api_key="ollama", single_msg=True
        )
    else:
        raise ValueError(f"Unknown provider: {provider!r}")


def _call_claude(
    system: str, user: str, model: str, single_msg: bool = False
) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    if single_msg or not system:
        msg = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": user}],
        )
    else:
        msg = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    return msg.content[0].text.strip()


def _call_openai(
    system: str,
    user: str,
    model: str,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    single_msg: bool = False,
) -> str:
    from openai import OpenAI
    client = OpenAI(
        api_key=api_key or os.environ.get("OPENAI_API_KEY", ""),
        base_url=base_url,
    )
    messages = []
    if not single_msg and system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_completion_tokens=4096,
    )
    return resp.choices[0].message.content.strip()
