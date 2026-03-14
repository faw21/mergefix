"""Tests for git utilities."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import tempfile
import os

from mergefix.git_utils import (
    find_conflicted_files,
    get_repo_root,
    is_merging,
    read_file,
    write_file,
)


def test_read_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello\nworld\n")
    content = read_file(str(tmp_path), "test.txt")
    assert content == "hello\nworld\n"


def test_write_file(tmp_path):
    write_file(str(tmp_path), "out.py", "x = 1\n")
    content = (tmp_path / "out.py").read_text()
    assert content == "x = 1\n"


def test_is_merging_false(tmp_path):
    # Not a git repo, no MERGE_HEAD → not merging
    result = is_merging(str(tmp_path))
    assert result is False


def test_is_merging_true(tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "MERGE_HEAD").write_text("abc123\n")
    result = is_merging(str(tmp_path))
    assert result is True


@patch("mergefix.git_utils._run")
def test_find_conflicted_files(mock_run):
    mock_run.return_value = "src/auth.py\nsrc/utils.py\n"
    files = find_conflicted_files("/fake/repo")
    assert files == ["src/auth.py", "src/utils.py"]
    mock_run.assert_called_once()


@patch("mergefix.git_utils._run")
def test_find_conflicted_files_empty(mock_run):
    mock_run.return_value = ""
    files = find_conflicted_files("/fake/repo")
    assert files == []


@patch("mergefix.git_utils._run")
def test_stage_file(mock_run, tmp_path):
    from mergefix.git_utils import stage_file
    mock_run.return_value = ""
    stage_file(str(tmp_path), "foo.py")
    mock_run.assert_called_once_with(["git", "add", "foo.py"], cwd=str(tmp_path))


@patch("subprocess.run")
def test_get_repo_root_success(mock_subproc):
    mock_subproc.return_value = MagicMock(returncode=0, stdout="/some/repo\n")
    root = get_repo_root()
    assert root == "/some/repo"


@patch("subprocess.run")
def test_get_repo_root_not_git(mock_subproc):
    mock_subproc.return_value = MagicMock(returncode=128, stdout="")
    root = get_repo_root()
    assert root is None


@patch("mergefix.git_utils._run")
def test_get_branch_names_simple(mock_run, tmp_path):
    from mergefix.git_utils import get_branch_names
    mock_run.return_value = "main"
    ours, theirs = get_branch_names(str(tmp_path))
    assert ours == "main"
    assert theirs == "MERGE_HEAD"


@patch("mergefix.git_utils._run")
def test_get_branch_names_with_merge_msg(mock_run, tmp_path):
    from mergefix.git_utils import get_branch_names
    mock_run.return_value = "main"
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "MERGE_MSG").write_text("Merge branch 'feature' into main\n")
    ours, theirs = get_branch_names(str(tmp_path))
    assert ours == "main"
    assert theirs == "feature"


@patch("subprocess.run")
def test_run_raises_on_stderr(mock_subproc):
    from mergefix.git_utils import _run, GitError
    mock_subproc.return_value = MagicMock(returncode=1, stderr="fatal: bad flag", stdout="")
    with pytest.raises(GitError, match="fatal: bad flag"):
        _run(["git", "bad-command"], cwd=".")
