"""Tests for the conflict parser."""

from pathlib import Path
import pytest
from mergefix.parser import (
    apply_resolutions,
    parse_conflicts,
)


# ── Test fixtures ─────────────────────────────────────────────────────────────

SIMPLE_CONFLICT = (
    "def greet(name):\n"
    "<<<<<<< HEAD\n"
    '    return f"Hello, {name}!"\n'
    "=======\n"
    '    return f"Hi there, {name}!"\n'
    ">>>>>>> feature/greeting\n"
)

DIFF3_CONFLICT = (
    "x = 1\n"
    "<<<<<<< HEAD\n"
    "x = 42\n"
    "||||||| base\n"
    "x = 10\n"
    "=======\n"
    "x = 99\n"
    ">>>>>>> feature\n"
    "y = 2\n"
)

MULTI_CONFLICT = (
    "line1\n"
    "<<<<<<< HEAD\n"
    "ours1\n"
    "=======\n"
    "theirs1\n"
    ">>>>>>> branch\n"
    "line2\n"
    "<<<<<<< HEAD\n"
    "ours2\n"
    "=======\n"
    "theirs2\n"
    ">>>>>>> branch\n"
    "line3\n"
)

MULTI_LINE_CONFLICT = (
    "class Foo:\n"
    "<<<<<<< HEAD\n"
    "    def bar(self):\n"
    "        return 1\n"
    "\n"
    "    def baz(self):\n"
    "        return 2\n"
    "=======\n"
    "    def bar(self):\n"
    "        return 100\n"
    ">>>>>>> other\n"
    "    pass\n"
)


# ── Basic two-way conflict ────────────────────────────────────────────────────

def test_parse_simple_conflict():
    parsed = parse_conflicts(SIMPLE_CONFLICT, Path("test.py"))
    assert parsed.has_conflicts
    assert parsed.conflict_count == 1
    c = parsed.conflicts[0]
    assert c.ours == '    return f"Hello, {name}!"'
    assert c.theirs == '    return f"Hi there, {name}!"'
    assert c.ours_label == "HEAD"
    assert c.theirs_label == "feature/greeting"
    assert c.base == ""


def test_parse_no_conflicts():
    content = "def foo():\n    return 42\n"
    parsed = parse_conflicts(content, Path("test.py"))
    assert not parsed.has_conflicts
    assert parsed.conflict_count == 0


def test_parse_multiple_conflicts():
    parsed = parse_conflicts(MULTI_CONFLICT)
    assert parsed.conflict_count == 2
    assert parsed.conflicts[0].ours == "ours1"
    assert parsed.conflicts[1].ours == "ours2"


# ── Diff3 style (3-way) ───────────────────────────────────────────────────────

def test_parse_diff3_conflict():
    parsed = parse_conflicts(DIFF3_CONFLICT)
    assert parsed.conflict_count == 1
    c = parsed.conflicts[0]
    assert c.ours == "x = 42"
    assert c.base == "x = 10"
    assert c.theirs == "x = 99"


# ── Multi-line conflicts ──────────────────────────────────────────────────────

def test_parse_multiline_conflict():
    parsed = parse_conflicts(MULTI_LINE_CONFLICT)
    assert parsed.conflict_count == 1
    c = parsed.conflicts[0]
    assert "def bar" in c.ours
    assert "return 1" in c.ours
    assert "def baz" in c.ours
    assert "return 100" in c.theirs


# ── apply_resolutions ─────────────────────────────────────────────────────────

def test_apply_single_resolution():
    parsed = parse_conflicts(SIMPLE_CONFLICT, Path("test.py"))
    resolution = '    return f"Hello there, {name}!"'
    result = apply_resolutions(
        parsed.original_content,
        parsed.conflicts,
        [resolution],
    )
    assert "<<<<<<" not in result
    assert "=======" not in result
    assert ">>>>>>>" not in result
    assert "Hello there" in result


def test_apply_multiple_resolutions():
    parsed = parse_conflicts(MULTI_CONFLICT)
    result = apply_resolutions(
        parsed.original_content,
        parsed.conflicts,
        ["b_and_c", "e_and_f"],
    )
    assert "<<<<<<" not in result
    assert "b_and_c" in result
    assert "e_and_f" in result
    assert "line1\n" in result
    assert "line3\n" in result


def test_apply_empty_resolution():
    content = (
        "before\n"
        "<<<<<<< HEAD\n"
        "to_delete\n"
        "=======\n"
        "also_delete\n"
        ">>>>>>> branch\n"
        "after\n"
    )
    parsed = parse_conflicts(content)
    result = apply_resolutions(
        parsed.original_content,
        parsed.conflicts,
        [""],
    )
    assert "to_delete" not in result
    assert "also_delete" not in result
    assert "before\n" in result
    assert "after\n" in result


def test_apply_wrong_number_of_resolutions():
    parsed = parse_conflicts(SIMPLE_CONFLICT)
    with pytest.raises(ValueError, match="Expected 1 resolutions"):
        apply_resolutions(parsed.original_content, parsed.conflicts, ["a", "b"])


# ── Line number tracking ──────────────────────────────────────────────────────

def test_conflict_line_numbers():
    parsed = parse_conflicts(SIMPLE_CONFLICT, Path("test.py"))
    c = parsed.conflicts[0]
    lines = SIMPLE_CONFLICT.splitlines()
    assert lines[c.start_line].startswith("<<<<<<<")
    assert lines[c.end_line].startswith(">>>>>>>")


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_conflict_at_file_start():
    content = (
        "<<<<<<< HEAD\n"
        "ours\n"
        "=======\n"
        "theirs\n"
        ">>>>>>> branch\n"
        "rest of file\n"
    )
    parsed = parse_conflicts(content)
    assert parsed.conflict_count == 1


def test_conflict_at_file_end():
    content = (
        "start of file\n"
        "<<<<<<< HEAD\n"
        "ours\n"
        "=======\n"
        "theirs\n"
        ">>>>>>> branch"
    )
    parsed = parse_conflicts(content)
    assert parsed.conflict_count == 1


def test_empty_ours_side():
    content = (
        "<<<<<<< HEAD\n"
        "=======\n"
        "theirs only\n"
        ">>>>>>> branch\n"
    )
    parsed = parse_conflicts(content)
    assert parsed.conflict_count == 1
    assert parsed.conflicts[0].ours == ""
    assert parsed.conflicts[0].theirs == "theirs only"


def test_empty_theirs_side():
    content = (
        "<<<<<<< HEAD\n"
        "ours only\n"
        "=======\n"
        ">>>>>>> branch\n"
    )
    parsed = parse_conflicts(content)
    assert parsed.conflict_count == 1
    assert parsed.conflicts[0].ours == "ours only"
    assert parsed.conflicts[0].theirs == ""
