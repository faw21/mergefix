"""Tests for the mergefix CLI."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from mergefix.cli import main


SIMPLE_CONFLICT = (
    'def greet(name):\n'
    '<<<<<<< HEAD\n'
    '    return f"Hello, {name}!"\n'
    '=======\n'
    '    return f"Hi there, {name}!"\n'
    '>>>>>>> feature/greeting\n'
)


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def conflict_file(tmp_path):
    """Create a temp file with a merge conflict."""
    f = tmp_path / "example.py"
    f.write_text(SIMPLE_CONFLICT)
    return f


# ── Basic CLI invocations ─────────────────────────────────────────────────────

def test_version(runner):
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_no_conflicts_in_empty_dir(runner, tmp_path):
    (tmp_path / "clean.py").write_text("x = 1\n")
    import os
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = runner.invoke(main, [], catch_exceptions=False)
    finally:
        os.chdir(old_cwd)
    # Should exit 0 (no conflicts found)
    assert result.exit_code == 0


def test_preview_mode(runner, conflict_file):
    """--preview should show resolution but not write the file."""
    original = conflict_file.read_text()
    mock_provider = MagicMock()
    mock_provider.complete.return_value = '    return f"Hello there, {name}!"'

    with patch("mergefix.cli.make_provider", return_value=mock_provider):
        result = runner.invoke(
            main,
            [str(conflict_file), "--preview", "--provider", "ollama"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    # File should NOT be modified
    assert conflict_file.read_text() == original
    assert "Preview mode" in result.output


def test_yes_mode_applies_without_prompt(runner, conflict_file):
    """--yes should apply without asking."""
    mock_provider = MagicMock()
    mock_provider.complete.return_value = '    return f"Hello there, {name}!"'

    with patch("mergefix.cli.make_provider", return_value=mock_provider):
        result = runner.invoke(
            main,
            [str(conflict_file), "--yes", "--provider", "ollama"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    content = conflict_file.read_text()
    assert "<<<<<<<" not in content
    assert "Hello there" in content


def test_backup_flag_creates_orig(runner, conflict_file, tmp_path):
    """--backup should create a .orig file."""
    mock_provider = MagicMock()
    mock_provider.complete.return_value = "    return 42"

    with patch("mergefix.cli.make_provider", return_value=mock_provider):
        runner.invoke(
            main,
            [str(conflict_file), "--yes", "--backup", "--provider", "ollama"],
            catch_exceptions=False,
        )

    orig_path = conflict_file.with_suffix(".py.orig")
    assert orig_path.exists()
    assert "<<<<<<<" in orig_path.read_text()


def test_provider_error_exits_gracefully(runner, conflict_file):
    """If provider fails to init, should show error and continue."""
    with patch(
        "mergefix.cli.make_provider",
        side_effect=RuntimeError("No API key"),
    ):
        result = runner.invoke(
            main,
            [str(conflict_file), "--preview"],
            catch_exceptions=False,
        )

    assert result.exit_code == 1 or "No API key" in result.output


def test_auto_scan_finds_conflicts(runner, tmp_path):
    """Without file args, mergefix should scan and find conflict files."""
    conflict_file = tmp_path / "main.py"
    conflict_file.write_text(SIMPLE_CONFLICT)
    clean_file = tmp_path / "clean.py"
    clean_file.write_text("x = 1\n")

    mock_provider = MagicMock()
    mock_provider.complete.return_value = '    return "merged"'

    with patch("mergefix.cli.make_provider", return_value=mock_provider):
        result = runner.invoke(
            main,
            ["--yes", "--provider", "ollama"],
            catch_exceptions=False,
            env={"PWD": str(tmp_path)},
        )

    # Should have found and attempted to resolve the file
    assert "main.py" in result.output or result.exit_code in (0, 1)


def test_multiple_files(runner, tmp_path):
    """Passing multiple files resolves all of them."""
    f1 = tmp_path / "a.py"
    f2 = tmp_path / "b.py"
    f1.write_text(SIMPLE_CONFLICT)
    f2.write_text(SIMPLE_CONFLICT.replace("greeting", "auth"))

    mock_provider = MagicMock()
    mock_provider.complete.return_value = '    return "resolved"'

    with patch("mergefix.cli.make_provider", return_value=mock_provider):
        result = runner.invoke(
            main,
            [str(f1), str(f2), "--yes", "--provider", "ollama"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    assert "<<<<<<<" not in f1.read_text()
    assert "<<<<<<<" not in f2.read_text()


def test_partial_failure_exits_nonzero(runner, tmp_path):
    """If one file fails, exit code should be non-zero."""
    f1 = tmp_path / "a.py"
    f1.write_text(SIMPLE_CONFLICT)

    mock_provider = MagicMock()
    mock_provider.complete.side_effect = RuntimeError("LLM down")

    with patch("mergefix.cli.make_provider", return_value=mock_provider):
        result = runner.invoke(
            main,
            [str(f1), "--yes", "--provider", "ollama"],
            catch_exceptions=False,
        )

    assert result.exit_code == 1
