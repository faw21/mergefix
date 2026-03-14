"""
Integration tests with real LLM calls.
Tests that mergefix actually resolves conflicts end-to-end.
"""

import os
import pytest
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("/Users/aaronwu/Local/my-projects/give-it-all/.env", override=True)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


PYTHON_CONFLICT = (
    "def calculate_discount(price, user_type):\n"
    "<<<<<<< HEAD\n"
    "    if user_type == \"premium\":\n"
    "        return price * 0.80\n"
    "    return price * 0.95\n"
    "=======\n"
    "    if user_type == \"premium\":\n"
    "        return price * 0.75\n"
    "    elif user_type == \"vip\":\n"
    "        return price * 0.60\n"
    "    return price\n"
    ">>>>>>> feature/pricing\n"
)


@pytest.mark.skipif(not ANTHROPIC_API_KEY, reason="ANTHROPIC_API_KEY not set")
def test_real_claude_resolves_python_conflict():
    """Real Claude call resolves a Python function conflict."""
    from mergefix.parser import parse_conflicts
    from mergefix.providers import ClaudeProvider
    from mergefix.resolver import resolve_file

    parsed = parse_conflicts(PYTHON_CONFLICT, Path("pricing.py"))
    assert parsed.conflict_count == 1, f"Expected 1 conflict, got {parsed.conflict_count}"

    provider = ClaudeProvider(model="claude-haiku-4-5-20251001")
    results = resolve_file(parsed, provider)

    assert len(results) == 1
    r = results[0]
    assert r.success, f"Resolution failed: {r.error}"
    assert "<<<<<<" not in r.resolution
    assert "=======" not in r.resolution
    assert ">>>>>>>" not in r.resolution
    assert "return" in r.resolution

    print(f"\n\u2705 Claude resolved conflict:\n{r.resolution}")


@pytest.mark.skipif(not OPENAI_API_KEY, reason="OPENAI_API_KEY not set")
def test_real_openai_resolves_conflict():
    """Real OpenAI call resolves a conflict."""
    from mergefix.parser import parse_conflicts
    from mergefix.providers import OpenAIProvider
    from mergefix.resolver import resolve_file

    parsed = parse_conflicts(PYTHON_CONFLICT, Path("pricing.py"))
    provider = OpenAIProvider(model="gpt-4o-mini")

    results = resolve_file(parsed, provider)

    assert len(results) == 1
    r = results[0]
    assert r.success, f"Resolution failed: {r.error}"
    assert "<<<<<<" not in r.resolution
    assert "return" in r.resolution

    print(f"\n\u2705 OpenAI resolved conflict:\n{r.resolution}")


@pytest.mark.skipif(not ANTHROPIC_API_KEY, reason="ANTHROPIC_API_KEY not set")
def test_real_llm_resolves_multiple_conflicts():
    """Real LLM resolves a file with 2 conflicts."""
    from mergefix.parser import parse_conflicts, apply_resolutions
    from mergefix.providers import ClaudeProvider
    from mergefix.resolver import resolve_file

    content = (
        "# config.py\n"
        "<<<<<<< HEAD\n"
        "DEBUG = False\n"
        'LOG_LEVEL = "WARNING"\n'
        "=======\n"
        "DEBUG = True\n"
        'LOG_LEVEL = "DEBUG"\n'
        "VERBOSE = True\n"
        ">>>>>>> dev-settings\n"
        "\n"
        'app_name = "myapp"\n'
        "\n"
        "<<<<<<< HEAD\n"
        "MAX_CONNECTIONS = 100\n"
        "TIMEOUT = 30\n"
        "=======\n"
        "MAX_CONNECTIONS = 50\n"
        "TIMEOUT = 60\n"
        "RETRY = 3\n"
        ">>>>>>> feature/limits\n"
    )
    parsed = parse_conflicts(content, Path("config.py"))
    assert parsed.conflict_count == 2, f"Expected 2 conflicts, got {parsed.conflict_count}"

    provider = ClaudeProvider(model="claude-haiku-4-5-20251001")
    results = resolve_file(parsed, provider)

    assert len(results) == 2
    for r in results:
        assert r.success, f"Failed: {r.error}"
        assert "<<<<<<" not in r.resolution

    resolved = apply_resolutions(content, parsed.conflicts, [r.resolution for r in results])
    assert "<<<<<<" not in resolved
    assert "app_name" in resolved

    print(f"\n\u2705 Claude resolved 2 conflicts:\n{resolved}")
