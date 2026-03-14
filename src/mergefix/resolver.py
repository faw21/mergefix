"""
Build prompts and parse AI responses for merge conflict resolution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .parser import ConflictBlock, ParsedFile

if TYPE_CHECKING:
    from .providers import LLMProvider


@dataclass
class ResolutionResult:
    """Result of resolving a single conflict block."""
    conflict: ConflictBlock
    resolution: str
    success: bool
    error: str = ""


def resolve_file(parsed: ParsedFile, provider: "LLMProvider") -> list[ResolutionResult]:
    """Resolve all conflict blocks in a parsed file using the given LLM provider."""
    file_ext = parsed.path.suffix.lower()
    results: list[ResolutionResult] = []
    for conflict in parsed.conflicts:
        try:
            prompt = build_prompt(conflict, file_ext)
            raw = provider.resolve(prompt)
            resolution = clean_response(raw)
            results.append(ResolutionResult(conflict=conflict, resolution=resolution, success=True))
        except Exception as exc:
            results.append(ResolutionResult(conflict=conflict, resolution="", success=False, error=str(exc)))
    return results


_SYSTEM_HINT = """\
You are a senior software engineer resolving a git merge conflict.
You will receive the conflicting code sections and must produce the correct merged result.

Rules:
1. Output ONLY the resolved code — no explanations, no markdown fences, no extra text.
2. Preserve the logic from both sides when appropriate; choose the better approach when they conflict.
3. If both sides do the same thing differently, prefer the cleaner/newer approach.
4. Maintain consistent indentation and style with the surrounding code.
5. If you genuinely cannot determine the correct merge, output the comment:
   # MERGEFIX: manual resolution required
   followed by both versions as comments.
"""


def build_prompt(conflict: ConflictBlock, file_ext: str = "") -> str:
    """Build the LLM prompt for a single conflict block."""
    lang_hint = ""
    EXT_TO_LANG = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".go": "Go", ".rs": "Rust", ".java": "Java", ".rb": "Ruby",
        ".cpp": "C++", ".c": "C", ".cs": "C#", ".php": "PHP",
        ".swift": "Swift", ".kt": "Kotlin",
    }
    if file_ext in EXT_TO_LANG:
        lang_hint = f"Language: {EXT_TO_LANG[file_ext]}\n"

    parts = [_SYSTEM_HINT, "", lang_hint]

    if conflict.context_before.strip():
        parts.append("Context before the conflict:")
        parts.append("```")
        parts.append(conflict.context_before.rstrip())
        parts.append("```")
        parts.append("")

    parts.append(f"<<<<<<< {conflict.ours_label} (OURS)")
    parts.append(conflict.ours.rstrip())

    if conflict.base.strip():
        parts.append("||||||| BASE (common ancestor)")
        parts.append(conflict.base.rstrip())

    parts.append("=======")
    parts.append(conflict.theirs.rstrip())
    parts.append(f">>>>>>> {conflict.theirs_label} (THEIRS)")

    if conflict.context_after.strip():
        parts.append("")
        parts.append("Context after the conflict:")
        parts.append("```")
        parts.append(conflict.context_after.rstrip())
        parts.append("```")

    parts.append("")
    parts.append("Output ONLY the resolved code:")
    return "\n".join(parts)


def clean_response(response: str) -> str:
    """Strip markdown fences and leading/trailing whitespace from AI response."""
    text = response.strip()
    # Strip ```lang ... ``` fences
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first and last fence lines
        start = 1
        end = len(lines)
        if lines[-1].strip() == "```":
            end = len(lines) - 1
        text = "\n".join(lines[start:end]).strip()
    return text


# Alias for backward compat
_strip_fences = clean_response


# ── Bridge for conflict.py API ────────────────────────────────────────────────

def resolve_conflict(
    conflict: "Conflict",
    provider: str = "claude",
    model: str | None = None,
) -> "ConflictResolution":
    """
    Resolve a single Conflict (from conflict.py) using AI.
    
    Returns a ConflictResolution dataclass with the resolved text.
    """
    from .conflict import Conflict
    from .providers import build_resolution_prompt, call_llm, detect_language
    
    lang_hint = detect_language(conflict.file_path)
    system, user = build_resolution_prompt(
        file_path=conflict.file_path,
        ours_label=conflict.ours_label,
        theirs_label=conflict.theirs_label,
        ours=conflict.ours,
        base=conflict.base,
        theirs=conflict.theirs,
        context_before=conflict.context_before,
        context_after=conflict.context_after,
        language_hint=lang_hint,
    )
    resolved_text = call_llm(system, user, provider=provider, model=model)
    resolved_text = clean_response(resolved_text)
    return ConflictResolution(conflict=conflict, resolved_text=resolved_text)


@dataclass
class ConflictResolution:
    """Result of resolving a Conflict from conflict.py."""
    conflict: "Conflict"
    resolved_text: str
    
    @property
    def strategy(self) -> str:
        return "ai"

# Re-export for backward compatibility with integration tests
from .providers import resolve_conflict
