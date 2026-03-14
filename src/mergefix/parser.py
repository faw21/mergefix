"""
Parse git conflict markers from file content.

Conflict format:
    <<<<<<< HEAD (or branch name)
    ... ours ...
    ======= (optional base section follows in diff3 style)
    ... theirs ...
    >>>>>>> feature-branch

Supports both 2-way (default) and 3-way (diff3) conflict styles.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


CONFLICT_START = re.compile(r"^<<<<<<< (.+)$")
CONFLICT_SEP = re.compile(r"^=======$")
CONFLICT_END = re.compile(r"^>>>>>>> (.+)$")
DIFF3_SEP = re.compile(r"^\|\|\|\|\|\|\| (.+)$")  # diff3 base marker


@dataclass
class ConflictBlock:
    """A single conflict block within a file."""

    start_line: int  # 0-indexed line of the <<<<<<< marker
    end_line: int    # 0-indexed line of the >>>>>>> marker
    ours_label: str
    theirs_label: str
    ours: str        # content from HEAD side
    base: str        # content from common ancestor (diff3 only, may be empty)
    theirs: str      # content from merging branch


@dataclass
class ParsedFile:
    """Result of parsing a file that may contain conflict markers."""

    path: Path
    original_content: str
    conflicts: list[ConflictBlock] = field(default_factory=list)

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0

    @property
    def conflict_count(self) -> int:
        return len(self.conflicts)


def parse_conflicts(content: str, path: Path | None = None) -> ParsedFile:
    """
    Parse all conflict blocks in file content.

    Handles both standard (2-way) and diff3-style (3-way) conflicts.
    """
    result = ParsedFile(
        path=path or Path("<string>"),
        original_content=content,
    )

    lines = content.splitlines()
    i = 0
    while i < len(lines):
        m = CONFLICT_START.match(lines[i])
        if not m:
            i += 1
            continue

        # Found start of conflict
        start_line = i
        ours_label = m.group(1)
        ours_lines: list[str] = []
        base_lines: list[str] = []
        theirs_lines: list[str] = []
        theirs_label = ""

        i += 1
        state = "ours"

        while i < len(lines):
            line = lines[i]

            if DIFF3_SEP.match(line):
                # diff3 base section starts
                state = "base"
                i += 1
                continue

            if CONFLICT_SEP.match(line):
                state = "theirs"
                i += 1
                continue

            end_m = CONFLICT_END.match(line)
            if end_m:
                theirs_label = end_m.group(1)
                end_line = i
                result.conflicts.append(
                    ConflictBlock(
                        start_line=start_line,
                        end_line=end_line,
                        ours_label=ours_label,
                        theirs_label=theirs_label,
                        ours="\n".join(ours_lines),
                        base="\n".join(base_lines),
                        theirs="\n".join(theirs_lines),
                    )
                )
                i += 1
                break

            if state == "ours":
                ours_lines.append(line)
            elif state == "base":
                base_lines.append(line)
            else:
                theirs_lines.append(line)

            i += 1

    return result


def find_conflict_files(root: Path) -> list[Path]:
    """
    Return all files under root that contain conflict markers.
    Skips binary files and common non-source directories.
    """
    SKIP_DIRS = {
        ".git", ".hg", ".svn",
        "node_modules", "__pycache__", ".venv", "venv",
        ".tox", "dist", "build", ".eggs",
    }
    results: list[Path] = []

    for p in root.rglob("*"):
        if not p.is_file():
            continue
        # Skip files in ignored directories
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        # Skip binary files (quick heuristic)
        try:
            content = p.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, PermissionError):
            continue
        if "<<<<<<< " in content:
            results.append(p)

    return sorted(results)


def apply_resolutions(
    original_content: str,
    conflicts: list[ConflictBlock],
    resolutions: list[str],
) -> str:
    """
    Replace conflict blocks in original_content with the resolved strings.

    resolutions[i] corresponds to conflicts[i].
    """
    if len(conflicts) != len(resolutions):
        raise ValueError(
            f"Expected {len(conflicts)} resolutions, got {len(resolutions)}"
        )

    lines = original_content.splitlines(keepends=True)
    # Process in reverse order to preserve line numbers
    for conflict, resolution in reversed(list(zip(conflicts, resolutions))):
        start = conflict.start_line
        end = conflict.end_line
        # Build replacement: resolution lines + trailing newline
        replacement = resolution
        if not replacement.endswith("\n") and replacement:
            replacement += "\n"
        lines[start : end + 1] = [replacement] if replacement else []

    return "".join(lines)
