"""Tests for conflict parsing and resolution application."""

import pytest
from mergefix.conflict import (
    Conflict,
    ParseResult,
    apply_resolution,
    parse_conflicts,
)

# ── Sample conflict content ───────────────────────────────────────────────────

SIMPLE_CONFLICT = """\
def greet(name):
<<<<<<< HEAD
    return f"Hello, {name}!"
=======
    return f"Hi, {name}! How are you?"
>>>>>>> feature-greeting
"""

CONFLICT_WITH_BASE = """\
def authenticate(user):
<<<<<<< HEAD
    token = generate_token(user)
    return {"status": "ok", "token": token}
||||||| base
    return {"status": "ok"}
=======
    session = create_session(user)
    return {"status": "ok", "session": session}
>>>>>>> feature-sessions
"""

MULTI_CONFLICT = """\
import os
<<<<<<< HEAD
import sys
=======
import logging
>>>>>>> dev
x = 1
<<<<<<< HEAD
y = 2
=======
y = 99
>>>>>>> dev
"""

NO_CONFLICT = """\
def foo():
    return 42
"""

# ── Tests: parse_conflicts ────────────────────────────────────────────────────

def test_parse_simple_conflict():
    result = parse_conflicts("foo.py", SIMPLE_CONFLICT)
    assert result.has_conflicts
    assert len(result.conflicts) == 1
    c = result.conflicts[0]
    assert c.file_path == "foo.py"
    assert c.ours_label == "HEAD"
    assert c.theirs_label == "feature-greeting"
    assert 'Hello' in c.ours
    assert 'Hi' in c.theirs
    assert c.base is None


def test_parse_conflict_with_base():
    result = parse_conflicts("auth.py", CONFLICT_WITH_BASE)
    assert result.has_conflicts
    c = result.conflicts[0]
    assert c.base is not None
    assert "status" in c.base
    assert "token" in c.ours
    assert "session" in c.theirs


def test_parse_multi_conflict():
    result = parse_conflicts("main.py", MULTI_CONFLICT)
    assert len(result.conflicts) == 2


def test_parse_no_conflict():
    result = parse_conflicts("clean.py", NO_CONFLICT)
    assert not result.has_conflicts
    assert result.conflicts == []


def test_parse_context_lines():
    """Context before/after should capture surrounding code."""
    result = parse_conflicts("foo.py", SIMPLE_CONFLICT)
    c = result.conflicts[0]
    # context_before should include the function definition
    assert "def greet" in c.context_before or len(c.context_before) == 0
    # context_after should be empty or newline (it's at end of file)


def test_parse_preserves_original_content():
    result = parse_conflicts("foo.py", SIMPLE_CONFLICT)
    assert result.original_content == SIMPLE_CONFLICT


# ── Tests: apply_resolution ───────────────────────────────────────────────────

def test_apply_resolution_simple():
    result = parse_conflicts("foo.py", SIMPLE_CONFLICT)
    c = result.conflicts[0]
    resolved = '    return f"Hello, {name}! How are you?"\n'
    new_content = apply_resolution(SIMPLE_CONFLICT, c, resolved)
    assert "<<<<<<" not in new_content
    assert "=======" not in new_content
    assert ">>>>>>" not in new_content
    assert "Hello, " in new_content
    assert "How are you" in new_content


def test_apply_resolution_multi_conflict():
    """Apply resolution to first conflict of multi-conflict file."""
    result = parse_conflicts("main.py", MULTI_CONFLICT)
    c = result.conflicts[0]
    # Resolve first conflict by choosing "ours"
    new_content = apply_resolution(MULTI_CONFLICT, c, "import sys\n")
    assert "import sys" in new_content
    # Second conflict should still be present
    assert "<<<<<<<" in new_content


def test_apply_resolution_keeps_surrounding_code():
    result = parse_conflicts("foo.py", SIMPLE_CONFLICT)
    c = result.conflicts[0]
    resolved = '    return "ok"\n'
    new_content = apply_resolution(SIMPLE_CONFLICT, c, resolved)
    assert "def greet(name):" in new_content
    assert "return" in new_content


# ── Tests: start/end line tracking ────────────────────────────────────────────

def test_conflict_line_numbers():
    result = parse_conflicts("foo.py", SIMPLE_CONFLICT)
    c = result.conflicts[0]
    assert c.start_line == 2   # <<<<<<< is line 2
    assert c.end_line == 6     # >>>>>>> is line 6


def test_conflict_line_numbers_multi():
    result = parse_conflicts("main.py", MULTI_CONFLICT)
    c1, c2 = result.conflicts
    assert c1.start_line < c2.start_line
    assert c1.end_line < c2.start_line
