"""Tests for prompt building and response cleaning."""

from mergefix.parser import ConflictBlock
from mergefix.resolver import build_prompt, clean_response


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
