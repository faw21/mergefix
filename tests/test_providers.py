"""Tests for providers module."""

import pytest
from mergefix.providers import build_resolution_prompt, detect_language


def test_build_resolution_prompt_basic():
    system, user = build_resolution_prompt(
        file_path="auth.py",
        ours_label="HEAD",
        theirs_label="feature",
        ours="    token = new_token()\n",
        base=None,
        theirs="    session = new_session()\n",
        context_before="def authenticate():\n",
        context_after="    return result\n",
    )
    assert "auth.py" in user
    assert "HEAD" in user
    assert "feature" in user
    assert "token" in user
    assert "session" in user
    assert "context_before" in user
    assert "conflict" in user


def test_build_resolution_prompt_with_base():
    system, user = build_resolution_prompt(
        file_path="main.py",
        ours_label="HEAD",
        theirs_label="dev",
        ours="x = 1\n",
        base="x = 0\n",
        theirs="x = 2\n",
        context_before="",
        context_after="",
    )
    assert "base_original" in user
    assert "x = 0" in user


def test_build_resolution_prompt_no_context():
    system, user = build_resolution_prompt(
        file_path="foo.py",
        ours_label="HEAD",
        theirs_label="dev",
        ours="a\n",
        base=None,
        theirs="b\n",
        context_before="",
        context_after="",
    )
    # No context_before section when empty
    assert "context_before" not in user


def test_detect_language():
    assert detect_language("foo.py") != ""  # Python has a hint
    assert detect_language("bar.go") != ""  # Go has a hint
    assert detect_language("baz.rs") != ""  # Rust has a hint
    assert detect_language("unknown.xyz") == ""  # Unknown → empty


def test_system_prompt_has_instructions():
    system, _ = build_resolution_prompt(
        file_path="x.py",
        ours_label="HEAD",
        theirs_label="dev",
        ours="a\n",
        base=None,
        theirs="b\n",
        context_before="",
        context_after="",
    )
    assert "conflict" in system.lower()
    assert "conflict markers" in system.lower() or "marker" in system.lower()
