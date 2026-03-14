"""Tests for the conflict resolver (mocked LLM)."""

from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from mergefix.parser import parse_conflicts
from mergefix.resolver import ResolutionResult, _strip_fences, resolve_file


# ── _strip_fences ─────────────────────────────────────────────────────────────

def test_strip_fences_python():
    text = "```python\nx = 1\ny = 2\n```"
    assert _strip_fences(text) == "x = 1\ny = 2"


def test_strip_fences_plain():
    text = "```\nx = 1\n```"
    assert _strip_fences(text) == "x = 1"


def test_strip_fences_no_fences():
    text = "x = 1\ny = 2"
    assert _strip_fences(text) == "x = 1\ny = 2"


def test_strip_fences_single_line_fence():
    text = "```python\ncode here"
    assert _strip_fences(text) == "```python\ncode here"


# ── resolve_file ──────────────────────────────────────────────────────────────

CONFLICT_CONTENT = (
    "def greet(name):\n"
    "<<<<<<< HEAD\n"
    '    return f"Hello, {name}!"\n'
    "=======\n"
    '    return f"Hi there, {name}!"\n'
    ">>>>>>> feature/greeting\n"
)

TWO_CONFLICT_CONTENT = (
    "a\n"
    "<<<<<<< HEAD\n"
    "ours_a\n"
    "=======\n"
    "theirs_a\n"
    ">>>>>>> feature\n"
    "d\n"
    "<<<<<<< HEAD\n"
    "ours_b\n"
    "=======\n"
    "theirs_b\n"
    ">>>>>>> feature\n"
    "e\n"
)


def test_resolve_file_single_conflict():
    parsed = parse_conflicts(CONFLICT_CONTENT, Path("test.py"))
    provider = MagicMock()
    provider.complete.return_value = '    return f"Hello there, {name}!"'

    results = resolve_file(parsed, provider)

    assert len(results) == 1
    assert results[0].success is True
    assert "Hello there" in results[0].resolution
    provider.complete.assert_called_once()


def test_resolve_file_no_conflicts():
    content = "def foo():\n    return 1\n"
    parsed = parse_conflicts(content, Path("test.py"))
    provider = MagicMock()

    results = resolve_file(parsed, provider)

    assert results == []
    provider.complete.assert_not_called()


def test_resolve_file_multiple_conflicts():
    parsed = parse_conflicts(TWO_CONFLICT_CONTENT, Path("test.py"))
    provider = MagicMock()
    provider.complete.side_effect = ["resolved_1", "resolved_2"]

    results = resolve_file(parsed, provider)

    assert len(results) == 2
    assert results[0].resolution == "resolved_1"
    assert results[1].resolution == "resolved_2"
    assert provider.complete.call_count == 2


def test_resolve_file_provider_error():
    parsed = parse_conflicts(CONFLICT_CONTENT, Path("test.py"))
    provider = MagicMock()
    provider.complete.side_effect = RuntimeError("API error")

    results = resolve_file(parsed, provider)

    assert len(results) == 1
    assert results[0].success is False
    assert "API error" in results[0].error


def test_resolve_file_strips_fences():
    parsed = parse_conflicts(CONFLICT_CONTENT, Path("test.py"))
    provider = MagicMock()
    provider.complete.return_value = "```python\n    return 42\n```"

    results = resolve_file(parsed, provider)

    assert results[0].success is True
    assert "```" not in results[0].resolution
    assert "return 42" in results[0].resolution


def test_resolve_includes_context_in_prompt():
    """Verify the user prompt contains both ours and theirs sections."""
    parsed = parse_conflicts(CONFLICT_CONTENT, Path("test.py"))
    provider = MagicMock()
    provider.complete.return_value = '    return "merged"'

    resolve_file(parsed, provider)

    # provider.complete called with (system_prompt, user_prompt)
    call_args = provider.complete.call_args
    assert call_args is not None
    # Check positional args
    args = call_args[0]
    assert len(args) == 2
    system, user = args
    assert "Hello" in user or "Hi" in user  # one of the conflict sides
    assert "greet" in user or "name" in user  # context from surrounding code


def test_resolve_result_dataclass():
    from mergefix.parser import ConflictBlock
    r = ResolutionResult(
        conflict=MagicMock(spec=ConflictBlock),
        resolution="fixed code",
        success=True,
    )
    assert r.error == ""
    assert r.success


def test_resolve_result_failure():
    from mergefix.parser import ConflictBlock
    r = ResolutionResult(
        conflict=MagicMock(spec=ConflictBlock),
        resolution="",
        success=False,
        error="network error",
    )
    assert not r.success
    assert "network" in r.error
