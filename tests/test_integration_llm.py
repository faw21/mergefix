"""Integration tests that call real LLM APIs — skipped without API keys."""

import os
import pytest
from dotenv import load_dotenv

load_dotenv("/Users/aaronwu/Local/my-projects/give-it-all/.env", override=True)

from mergefix.parser import parse_file
from mergefix.providers import resolve_conflict
from mergefix.resolver import build_prompt, clean_response

_LT = "<" * 7
_GT = ">" * 7

PYTHON_CONFLICT = (
    "class Config:\n"
    "    def __init__(self):\n"
    + _LT + " HEAD\n"
    "        self.debug = True\n"
    "        self.log_level = \"INFO\"\n"
    "=======\n"
    "        self.debug = False\n"
    "        self.log_level = \"WARNING\"\n"
    "        self.max_retries = 3\n"
    + _GT + " production-defaults\n"
)

JS_CONFLICT = (
    "function fetchData(url) {\n"
    + _LT + " HEAD\n"
    "  return fetch(url).then(r => r.json());\n"
    "=======\n"
    "  return fetch(url)\n"
    "    .then(r => r.json())\n"
    "    .catch(err => { console.error(err); return null; });\n"
    + _GT + " error-handling\n"
    "}\n"
)


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
def test_resolve_python_conflict_claude():
    parsed = parse_file(PYTHON_CONFLICT, context_lines=0)
    assert parsed.has_conflicts
    conflict = parsed.conflicts[0]
    prompt = build_prompt(conflict, ".py")
    raw = resolve_conflict(prompt, provider="claude")
    resolved = clean_response(raw)
    assert _LT[0] * 7 not in resolved
    assert "=======" not in resolved
    assert _GT[0] * 7 not in resolved
    assert len(resolved.strip()) > 0


@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)
def test_resolve_js_conflict_openai():
    parsed = parse_file(JS_CONFLICT, context_lines=0)
    assert parsed.has_conflicts
    conflict = parsed.conflicts[0]
    prompt = build_prompt(conflict, ".js")
    raw = resolve_conflict(prompt, provider="openai")
    resolved = clean_response(raw)
    assert _LT[0] * 7 not in resolved
    assert "fetch" in resolved


def test_resolve_conflict_ollama():
    """Test with Ollama (local). Skipped if Ollama not available."""
    import subprocess
    check = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    if check.returncode != 0:
        pytest.skip("Ollama not available")

    parsed = parse_file(PYTHON_CONFLICT, context_lines=0)
    assert parsed.has_conflicts
    conflict = parsed.conflicts[0]
    prompt = build_prompt(conflict, ".py")
    raw = resolve_conflict(prompt, provider="ollama")
    resolved = clean_response(raw)
    assert len(resolved.strip()) > 0
    assert _LT[0] * 7 not in resolved
