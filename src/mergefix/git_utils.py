"""
Git utilities: find conflicted files, read them, check merge state.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Optional, Tuple


class GitError(Exception):
    pass


def _run(args: List[str], cwd: str) -> str:
    result = subprocess.run(
        args, capture_output=True, text=True, cwd=cwd
    )
    if result.returncode != 0 and result.stderr:
        raise GitError(result.stderr.strip())
    return result.stdout


def find_conflicted_files(repo_root: str) -> List[str]:
    """
    Return list of files with merge conflicts (unmerged state).
    Uses `git diff --name-only --diff-filter=U`.
    """
    output = _run(
        ["git", "diff", "--name-only", "--diff-filter=U"],
        cwd=repo_root,
    )
    return [f.strip() for f in output.splitlines() if f.strip()]


def read_file(repo_root: str, relative_path: str) -> str:
    """Read a file's content."""
    path = Path(repo_root) / relative_path
    return path.read_text(encoding="utf-8", errors="replace")


def write_file(repo_root: str, relative_path: str, content: str) -> None:
    """Write resolved content to a file."""
    path = Path(repo_root) / relative_path
    path.write_text(content, encoding="utf-8")


def stage_file(repo_root: str, relative_path: str) -> None:
    """Stage a resolved file with `git add`."""
    _run(["git", "add", relative_path], cwd=repo_root)


def get_repo_root() -> Optional[str]:
    """Return the git repo root from cwd, or None if not in a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass
    return None


def is_merging(repo_root: str) -> bool:
    """Return True if the repo is currently in a merge state."""
    merge_head = Path(repo_root) / ".git" / "MERGE_HEAD"
    return merge_head.exists()


def get_branch_names(repo_root: str) -> Tuple[str, str]:
    """
    Return (ours_branch, theirs_branch) from MERGE_HEAD info.
    Falls back to ('HEAD', 'MERGE_HEAD') if unavailable.
    """
    try:
        ours = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root).strip()
    except GitError:
        ours = "HEAD"

    merge_msg_path = Path(repo_root) / ".git" / "MERGE_MSG"
    theirs = "MERGE_HEAD"
    if merge_msg_path.exists():
        msg = merge_msg_path.read_text()
        for line in msg.splitlines():
            if "Merge branch" in line or "Merge commit" in line:
                # Extract branch name from e.g. "Merge branch 'feature' into main"
                import re
                m = re.search(r"['\"]([^'\"]+)['\"]", line)
                if m:
                    theirs = m.group(1)
                break

    return ours, theirs
