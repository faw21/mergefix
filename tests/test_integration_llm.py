"""Integration tests that call real LLM APIs."""

import os
import pytest
from dotenv import load_dotenv

load_dotenv("/Users/aaronwu/Local/my-projects/give-it-all/.env", override=True)

from mergefix.conflict import parse_conflicts
from mergefix.resolver import resolve_conflict


PYTHON_CONFLICT = """\
class Config:
    def __init__(self):
<<<<<<< HEAD
        self.debug = True
        self.log_level = "INFO"
=======
        self.debug = False
        self.log_level = "WARNING"
        self.max_retries = 3
>>>>>>> production-defaults
"""

JS_CONFLICT = """\
function fetchData(url) {
<<<<<<< HEAD
  return fetch(url).then(r => r.json());
=======
  return fetch(url)
    .then(r => r.json())
    .catch(err => { console.error(err); return null; });
>>>>>>> error-handling
}
"""


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set"
)
def test_resolve_python_conflict_claude():
    result = parse_conflicts("config.py", PYTHON_CONFLICT)
    assert result.has_conflicts
    resolution = resolve_conflict(result.conflicts[0], provider="claude")
    resolved = resolution.resolved_text
    # Should contain no conflict markers
    assert "<<<<<<<" not in resolved
    assert "=======" not in resolved
    assert ">>>>>>>" not in resolved
    # Should preserve some reasonable combination
    assert len(resolved.strip()) > 0


@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set"
)
def test_resolve_js_conflict_openai():
    result = parse_conflicts("fetch.js", JS_CONFLICT)
    assert result.has_conflicts
    resolution = resolve_conflict(result.conflicts[0], provider="openai")
    resolved = resolution.resolved_text
    assert "<<<<<<<" not in resolved
    assert "fetch" in resolved  # should keep the fetch logic


def test_resolve_conflict_ollama():
    """Test with Ollama (local, always available)."""
    import subprocess
    check = subprocess.run(
        ["ollama", "list"], capture_output=True, text=True
    )
    if check.returncode != 0:
        pytest.skip("Ollama not available")

    result = parse_conflicts("config.py", PYTHON_CONFLICT)
    assert result.has_conflicts
    resolution = resolve_conflict(result.conflicts[0], provider="ollama")
    resolved = resolution.resolved_text
    assert len(resolved.strip()) > 0
    assert "<<<<<<<" not in resolved
