"""Tests for conflict block parsing."""

from mergefix.parser import apply_resolution, parse_file, find_conflict_files
import tempfile, os


CONFLICT_SIMPLE = """\
def greet(name):
<<<<<<< HEAD
    return f"Hello, {name}!"
=======
    return f"Hi there, {name}!"
>>>>>>> feature/friendlier-greeting
    # end
"""

CONFLICT_WITH_BASE = """\
x = 1
<<<<<<< HEAD
y = 100
||||||| merged common ancestors
y = 10
=======
y = 50
>>>>>>> other
z = 3
"""

NO_CONFLICT = """\
def foo():
    return 42
"""


def test_parse_no_conflicts():
    result = parse_file(NO_CONFLICT)
    assert not result.has_conflicts
    assert result.conflicts == []


def test_parse_simple_conflict():
    result = parse_file(CONFLICT_SIMPLE)
    assert result.has_conflicts
    assert len(result.conflicts) == 1
    c = result.conflicts[0]
    assert "HEAD" in c.ours_label
    assert "feature/friendlier-greeting" in c.theirs_label
    assert 'f"Hello, {name}!"' in c.ours
    assert 'f"Hi there, {name}!"' in c.theirs
    assert c.base == ""
    assert c.start_line == 1
    assert c.end_line == 5


def test_parse_diff3_conflict():
    result = parse_file(CONFLICT_WITH_BASE)
    assert result.has_conflicts
    c = result.conflicts[0]
    assert "y = 100" in c.ours
    assert "y = 10" in c.base
    assert "y = 50" in c.theirs


def test_context_captured():
    result = parse_file(CONFLICT_SIMPLE, context_lines=1)
    c = result.conflicts[0]
    assert "def greet" in c.context_before
    assert "# end" in c.context_after


def test_parse_multiple_conflicts():
    content = (
        "a = 1\n"
        "<<<<<<< main\n"
        "b = 2\n"
        "=======\n"
        "b = 20\n"
        ">>>>>>> dev\n"
        "c = 3\n"
        "<<<<<<< main\n"
        "d = 4\n"
        "=======\n"
        "d = 40\n"
        ">>>>>>> dev\n"
    )
    result = parse_file(content)
    assert result.has_conflicts
    assert len(result.conflicts) == 2


def test_apply_resolution_simple():
    content = CONFLICT_SIMPLE
    result = parse_file(content)
    new_content = apply_resolution(content, result.conflicts, ['    return f"Hello, {name}!"\n'])
    assert "<<<<<<<" not in new_content
    assert "=======" not in new_content
    assert ">>>>>>>" not in new_content
    assert 'f"Hello, {name}!"' in new_content


def test_apply_resolution_multiple():
    content = (
        "<<<<<<< a\n"
        "x=1\n"
        "=======\n"
        "x=10\n"
        ">>>>>>> b\n"
        "mid\n"
        "<<<<<<< a\n"
        "y=2\n"
        "=======\n"
        "y=20\n"
        ">>>>>>> b\n"
    )
    result = parse_file(content)
    new_content = apply_resolution(content, result.conflicts, ["x=1\n", "y=20\n"])
    assert "x=1" in new_content
    assert "y=20" in new_content
    assert "<<<<<<<" not in new_content


def test_find_conflict_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        f1 = os.path.join(tmpdir, "file1.py")
        f2 = os.path.join(tmpdir, "file2.py")
        f3 = os.path.join(tmpdir, "file3.py")

        with open(f1, "w") as f:
            f.write(CONFLICT_SIMPLE)
        with open(f2, "w") as f:
            f.write(NO_CONFLICT)
        with open(f3, "w") as f:
            f.write(CONFLICT_WITH_BASE)

        found = find_conflict_files([tmpdir])
        found_names = {os.path.basename(p) for p in found}
        assert "file1.py" in found_names
        assert "file3.py" in found_names
        assert "file2.py" not in found_names
