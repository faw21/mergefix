"""Tests for prompt building and response cleaning."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mergefix.parser import ConflictBlock, ParsedFile
from mergefix.resolver import (
    ResolutionResult,
    build_prompt,
    clean_response,
    resolve_file,
)


CONFLICT = ConflictBlock(
    start_line=5,
    end_line=10,
    ours_label="HEAD",
    theirs_label="feature",
    ours='    return "old"\n',
    theirs='    return "new"\n',
    base="",
    context_before="def greet():\n",
    context_after="",
)


def test_build_prompt_contains_ours_and_theirs():
    prompt = build_prompt(CONFLICT, ".py")
    assert "return" in prompt
    assert "HEAD" in prompt
    assert "feature" in prompt
    assert "OURS" in prompt
    assert "THEIRS" in prompt


def test_build_prompt_python_lang_hint():
    prompt = build_prompt(CONFLICT, ".py")
    assert "Python" in prompt


def test_build_prompt_context():
    prompt = build_prompt(CONFLICT, ".py")
    assert "def greet" in prompt


def test_build_prompt_with_base():
    conflict = ConflictBlock(
        start_line=1, end_line=10,
        ours_label="HEAD", theirs_label="other",
        ours="x = 1\n", theirs="x = 2\n", base="x = 0\n",
    )
    prompt = build_prompt(conflict, ".py")
    assert "BASE" in prompt
    assert "x = 0" in prompt


def test_clean_response_strips_fences():
    raw = "```python\nx = 1\n```"
    assert clean_response(raw) == "x = 1"


def test_clean_response_no_fence():
    raw = "x = 1\ny = 2"
    assert clean_response(raw) == "x = 1\ny = 2"


def test_clean_response_whitespace():
    raw = "\n\n  x = 1  \n\n"
    assert clean_response(raw) == "x = 1"


def test_clean_response_generic_fence():
    raw = "```\nx = 1\n```"
    assert clean_response(raw) == "x = 1"


# ── resolve_file tests ────────────────────────────────────────────────────────

def _make_parsed(conflicts):
    pf = ParsedFile(path=Path("test.py"), original_content="")
    pf.conflicts = conflicts
    return pf


def test_resolve_file_success():
    conflict = ConflictBlock(
        start_line=0, end_line=4,
        ours_label="HEAD", theirs_label="dev",
        ours="x = 1\n", theirs="x = 2\n", base="",
    )
    parsed = _make_parsed([conflict])

    provider = MagicMock()
    provider.resolve.return_value = "x = 1\n"

    results = resolve_file(parsed, provider)
    assert len(results) == 1
    assert results[0].success is True
    assert results[0].resolution == "x = 1"
    assert results[0].conflict is conflict


def test_resolve_file_provider_error():
    conflict = ConflictBlock(
        start_line=0, end_line=4,
        ours_label="HEAD", theirs_label="dev",
        ours="a\n", theirs="b\n", base="",
    )
    parsed = _make_parsed([conflict])

    provider = MagicMock()
    provider.resolve.side_effect = RuntimeError("API error")

    results = resolve_file(parsed, provider)
    assert len(results) == 1
    assert results[0].success is False
    assert "API error" in results[0].error
    assert results[0].resolution == ""


def test_resolve_file_multiple_conflicts():
    conflicts = [
        ConflictBlock(
            start_line=0, end_line=2,
            ours_label="HEAD", theirs_label="dev",
            ours="a = 1\n", theirs="a = 2\n", base="",
        ),
        ConflictBlock(
            start_line=5, end_line=7,
            ours_label="HEAD", theirs_label="dev",
            ours="b = 1\n", theirs="b = 2\n", base="",
        ),
    ]
    parsed = _make_parsed(conflicts)
    parsed.path = Path("test.py")

    provider = MagicMock()
    provider.resolve.side_effect = ["a = 1\n", "b = 2\n"]

    results = resolve_file(parsed, provider)
    assert len(results) == 2
    assert all(r.success for r in results)


def test_resolve_file_empty():
    parsed = _make_parsed([])
    provider = MagicMock()
    results = resolve_file(parsed, provider)
    assert results == []
    provider.resolve.assert_not_called()


def test_resolution_result_fields():
    conflict = ConflictBlock(
        start_line=0, end_line=1,
        ours_label="HEAD", theirs_label="dev",
        ours="x\n", theirs="y\n", base="",
    )
    r = ResolutionResult(conflict=conflict, resolution="x\n", success=True)
    assert r.error == ""
    assert r.success is True
