"""
Parse git merge conflict markers from file content.

Conflict format:
    <<<<<<< HEAD (or ours)
    ... our changes ...
    =======
    ... their changes ...
    >>>>>>> branch-name (or theirs)

With --diff3 base sections:
    <<<<<<< HEAD
    ... ours ...
    ||||||| base
    ... original ...
    =======
    ... theirs ...
    >>>>>>> branch
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


CONFLICT_START = re.compile(r"^<{7} (.+)$")
CONFLICT_BASE_SEP = re.compile(r"^\|{7} (.+)$")
CONFLICT_SEP = re.compile(r"^={7}$")
CONFLICT_END = re.compile(r"^>{7} (.+)$")

CONTEXT_LINES = 40  # lines of surrounding code to include for LLM context


@dataclass(frozen=True)
class Conflict:
    """A single merge conflict block within a file."""
    file_path: str
    start_line: int          # 1-based, line of <<<<<<<
    end_line: int            # 1-based, line of >>>>>>>
    ours_label: str          # e.g. "HEAD"
    theirs_label: str        # e.g. "feature-branch"
    ours: str                # our code
    base: Optional[str]      # original base (only with --diff3)
    theirs: str              # their code
    context_before: str      # N lines before conflict
    context_after: str       # N lines after conflict

    @property
    def full_block(self) -> str:
        """The raw conflict block as it appears in the file."""
        lines = [f"<<<<<<< {self.ours_label}", self.ours.rstrip()]
        if self.base is not None:
            lines += [f"||||||| base", self.base.rstrip()]
        lines += ["=======", self.theirs.rstrip(), f">>>>>>> {self.theirs_label}"]
        return "\n".join(lines)


@dataclass
class ParseResult:
    """Result of parsing conflicts in a file."""
    file_path: str
    original_content: str
    conflicts: List[Conflict]

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0


def parse_conflicts(file_path: str, content: str) -> ParseResult:
    """
    Parse all conflict blocks from file content.

    Returns ParseResult with list of Conflict objects.
    """
    lines = content.splitlines(keepends=True)
    conflicts: List[Conflict] = []

    i = 0
    while i < len(lines):
        m = CONFLICT_START.match(lines[i].rstrip("\n"))
        if not m:
            i += 1
            continue

        ours_label = m.group(1)
        start_line = i + 1  # 1-based

        # Collect ours section
        ours_lines: List[str] = []
        base_lines: Optional[List[str]] = None
        theirs_lines: List[str] = []
        theirs_label = ""
        end_line = start_line

        j = i + 1
        section = "ours"
        while j < len(lines):
            line = lines[j].rstrip("\n")

            if CONFLICT_BASE_SEP.match(line) and section == "ours":
                base_lines = []
                section = "base"
            elif CONFLICT_SEP.match(line) and section in ("ours", "base"):
                section = "theirs"
            elif (m2 := CONFLICT_END.match(line)):
                theirs_label = m2.group(1)
                end_line = j + 1  # 1-based
                break
            else:
                if section == "ours":
                    ours_lines.append(lines[j])
                elif section == "base" and base_lines is not None:
                    base_lines.append(lines[j])
                elif section == "theirs":
                    theirs_lines.append(lines[j])
            j += 1

        # Gather context (lines before and after)
        ctx_before_start = max(0, i - CONTEXT_LINES)
        ctx_before = "".join(lines[ctx_before_start:i])

        ctx_after_end = min(len(lines), j + 1 + CONTEXT_LINES)
        ctx_after = "".join(lines[j + 1:ctx_after_end])

        conflict = Conflict(
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            ours_label=ours_label,
            theirs_label=theirs_label,
            ours="".join(ours_lines),
            base="".join(base_lines) if base_lines is not None else None,
            theirs="".join(theirs_lines),
            context_before=ctx_before,
            context_after=ctx_after,
        )
        conflicts.append(conflict)
        i = j + 1

    return ParseResult(
        file_path=file_path,
        original_content=content,
        conflicts=conflicts,
    )


def apply_resolution(
    original_content: str, conflict: Conflict, resolved: str
) -> str:
    """
    Replace the conflict block in original_content with resolved text.

    Returns the new file content.
    """
    lines = original_content.splitlines(keepends=True)
    before = "".join(lines[:conflict.start_line - 1])
    after = "".join(lines[conflict.end_line:])

    # Ensure resolved ends with newline if original context has one
    resolved_text = resolved
    if not resolved_text.endswith("\n") and (
        conflict.end_line < len(lines) or original_content.endswith("\n")
    ):
        resolved_text += "\n"

    return before + resolved_text + after


def find_conflicted_files_in_content(files_with_content: List[Tuple[str, str]]) -> List[ParseResult]:
    """Parse conflicts from a list of (path, content) tuples."""
    results = []
    for path, content in files_with_content:
        result = parse_conflicts(path, content)
        if result.has_conflicts:
            results.append(result)
    return results
