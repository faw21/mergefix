"""CLI integration tests for mergefix."""

import os
import tempfile
from unittest.mock import patch

from click.testing import CliRunner

from mergefix.cli import main


CONFLICT_CONTENT = """\
def greet(name):
<<<<<<< HEAD
    return f"Hello, {name}!"
=======
    return f"Hi there, {name}!"
>>>>>>> feature
"""

CLEAN_CONTENT = """\
def foo():
    return 42
"""


def test_no_conflicts_exits_0():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("clean.py", "w") as f:
            f.write(CLEAN_CONTENT)
        result = runner.invoke(main, ["clean.py"])
    assert result.exit_code == 0
    assert result.output  # some success output


def test_dry_run_does_not_modify_file():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("conflict.py", "w") as f:
            f.write(CONFLICT_CONTENT)

        with patch("mergefix.cli.resolve_conflict", return_value='    return f"Hello, {name}!"\n'):
            result = runner.invoke(main, ["conflict.py", "--dry-run", "--provider", "claude"])

        # File should be unchanged
        with open("conflict.py") as f:
            content = f.read()
        assert "<<<<<<<" in content


def test_auto_applies_resolution():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("conflict.py", "w") as f:
            f.write(CONFLICT_CONTENT)

        resolution = '    return f"Hello, {name}!"\n'
        with patch("mergefix.cli.resolve_conflict", return_value=resolution):
            result = runner.invoke(
                main, ["conflict.py", "--auto", "--provider", "claude"]
            )

        with open("conflict.py") as f:
            content = f.read()
        assert "<<<<<<<" not in content
        assert "Hello" in content


def test_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert "0.2.0" in result.output


def test_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "mergefix" in result.output.lower()
