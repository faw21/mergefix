"""
AI-powered conflict resolver.

Sends each conflict block (with surrounding context) to the LLM
and asks it to produce the merged result.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .parser import ConflictBlock, ParsedFile
from .providers import LLMProvider


SYSTEM_PROMPT = """\
You are an expert software developer resolving git merge conflicts.

Your job: given a merge conflict block, produce the correct merged result.

Rules:
1. Output ONLY the resolved code — no conflict markers, no explanations, no markdown fences.
2. Preserve the intent of BOTH sides unless they are truly incompatible.
3. When in doubt, keep both changes (combine them intelligently).
4. Do NOT add or remove blank lines at the start/end unless necessary for correctness.
5. Match the indentation and style of the surrounding code.
6. If the two sides are doing the same thing differently, pick the cleaner version.
7. Never output <<<<<<, ======, or >>>>>>> markers in your response."""


def _get_commit_context(path: Path, label: str) -> str:
    """
    Try to get a brief commit message for the branch that introduced the change.
    Returns empty string on failure.
    """
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-3", label, "--", str(path)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def _build_user_prompt(
    conflict: ConflictBlock,
    file_content: str,
    commit_context_ours: str,
    commit_context_theirs: str,
    max_context_lines: int = 10,
) -> str:
    """Build the user prompt for a single conflict block."""
    lines = file_content.splitlines()

    # Context lines before and after the conflict
    before_start = max(0, conflict.start_line - max_context_lines)
    before_lines = lines[before_start : conflict.start_line]
    after_end = min(len(lines), conflict.end_line + 1 + max_context_lines)
    after_lines = lines[conflict.end_line + 1 : after_end]

    parts = ["Resolve this merge conflict:\n"]

    if commit_context_ours:
        parts.append(f"OUR changes ({conflict.ours_label}) come from:")
        parts.append(f"  {commit_context_ours}")
        parts.append("")

    if commit_context_theirs:
        parts.append(f"THEIR changes ({conflict.theirs_label}) come from:")
        parts.append(f"  {commit_context_theirs}")
        parts.append("")

    if before_lines:
        parts.append("--- Context before conflict ---")
        parts.append("\n".join(before_lines))
        parts.append("")

    parts.append(f"<<<<<<< {conflict.ours_label}")
    parts.append(conflict.ours)
    if conflict.base:
        parts.append(f"||||||| base")
        parts.append(conflict.base)
    parts.append("=======")
    parts.append(conflict.theirs)
    parts.append(f">>>>>>> {conflict.theirs_label}")

    if after_lines:
        parts.append("")
        parts.append("--- Context after conflict ---")
        parts.append("\n".join(after_lines))

    parts.append("\nOutput only the resolved code, nothing else.")

    return "\n".join(parts)


@dataclass
class ResolutionResult:
    conflict: ConflictBlock
    resolution: str
    success: bool
    error: str = ""


def resolve_file(
    parsed: ParsedFile,
    provider: LLMProvider,
) -> list[ResolutionResult]:
    """
    Resolve all conflicts in a ParsedFile using the given LLM provider.

    Returns one ResolutionResult per conflict, in order.
    """
    results: list[ResolutionResult] = []

    for conflict in parsed.conflicts:
        # Try to get commit context (best-effort)
        ours_ctx = _get_commit_context(parsed.path, conflict.ours_label)
        theirs_ctx = _get_commit_context(parsed.path, conflict.theirs_label)

        user_prompt = _build_user_prompt(
            conflict=conflict,
            file_content=parsed.original_content,
            commit_context_ours=ours_ctx,
            commit_context_theirs=theirs_ctx,
        )

        try:
            resolution = provider.complete(SYSTEM_PROMPT, user_prompt)
            # Strip markdown fences if LLM wraps in them
            resolution = _strip_fences(resolution)
            results.append(
                ResolutionResult(
                    conflict=conflict,
                    resolution=resolution,
                    success=True,
                )
            )
        except Exception as exc:
            results.append(
                ResolutionResult(
                    conflict=conflict,
                    resolution="",
                    success=False,
                    error=str(exc),
                )
            )

    return results


def _strip_fences(text: str) -> str:
    """Remove markdown code fences (```...```) if present."""
    lines = text.splitlines()
    if len(lines) >= 2 and lines[0].startswith("```"):
        # Remove first line (```language) and last line (```)
        end = len(lines) - 1
        while end > 0 and not lines[end].startswith("```"):
            end -= 1
        if end > 0:
            return "\n".join(lines[1:end])
    return text
