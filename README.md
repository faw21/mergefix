# mergefix

[![PyPI version](https://img.shields.io/pypi/v/mergefix.svg)](https://pypi.org/project/mergefix/)
[![Python](https://img.shields.io/pypi/pyversions/mergefix.svg)](https://pypi.org/project/mergefix/)

**AI-powered git merge conflict resolver — run one command, review the diff, apply.**

```
$ mergefix

╭──────────────────────────────────────────────────────╮
│ mergefix  ·  3 files  ·  7 conflicts  ·  provider: claude │
╰──────────────────────────────────────────────────────╯

→ src/auth.py (2 conflicts)

  Conflict 1/2
  ours: main
  theirs: feature/oauth
  ✓ Resolution:
    def authenticate(user, password):
        return bcrypt.checkpw(password.encode(), user.password_hash)

  Conflict 2/2
  ours: main
  theirs: feature/oauth
  ✓ Resolution:
    SESSION_TIMEOUT = 3600  # keep shorter timeout from main

Diff:
--- a/src/auth.py
+++ b/src/auth.py
@@ -12,7 +12,4 @@ def get_user(user_id):
-<<<<<<< HEAD
-    return hashlib.md5(password.encode()).hexdigest()
-=======
-    return bcrypt.checkpw(password.encode(), user.password_hash)
->>>>>>> feature/oauth
+    return bcrypt.checkpw(password.encode(), user.password_hash)

  Apply resolutions to src/auth.py? [Y/n] y
  ✓ Applied

✅ All 3 file(s) resolved.
Run `git diff` to review changes, then `git add` to mark as resolved.
```

## Install

```bash
pip install mergefix
```

Set your API key (or use Ollama for free local resolution):

```bash
export ANTHROPIC_API_KEY=your-key   # Claude (default, recommended)
export OPENAI_API_KEY=your-key      # or OpenAI
# or: mergefix --provider ollama    # local, no API key needed
```

## Usage

```bash
# Resolve all conflicts in the current repo (most common)
mergefix

# Resolve a specific file
mergefix src/auth.py src/db.py

# Preview resolutions without writing (safe to run anytime)
mergefix --preview

# Auto-apply all resolutions without prompting (CI/scripting)
mergefix --yes

# Keep original files as .orig backups
mergefix --backup

# Give the AI extra context about your codebase
mergefix --context "Python web app, prefer async patterns, strict type hints"

# Use local Ollama (free, no API key)
mergefix --provider ollama

# Use OpenAI
mergefix --provider openai --model gpt-4o
```

## How it works

1. Scans for files with `<<<<<<< ` conflict markers (or use specific files)
2. Parses each conflict block (supports 2-way and 3-way / diff3 style)
3. Calls the AI with both sides of each conflict + surrounding context
4. Displays each resolution in syntax-highlighted code blocks
5. Shows a colorized unified diff of all changes
6. Asks for confirmation before writing (skip with `--yes`)
7. Writes the resolved content; optionally creates `.orig` backups

The AI sees the **full file context**, not just the conflict lines — so it understands the surrounding code and makes semantically correct resolutions.

## Supports

- **Languages**: Any language (Python, JS, TypeScript, Go, Rust, Java, Ruby, etc.)
- **Conflict styles**: 2-way (default git) and 3-way / diff3
- **Providers**: Claude (default), OpenAI, Ollama (local, free)
- **Multiple conflicts**: Resolves all conflicts in a file in one AI call
- **Multiple files**: Processes all conflicted files in one run

## Pre-merge hook

Add to your workflow to catch issues early:

```bash
# After a merge, resolve all conflicts and review:
git merge feature-branch
mergefix --preview  # preview only
mergefix            # apply
git add -A
git commit
```

Or as a one-liner for scripting:

```bash
git merge feature-branch && mergefix --yes && git add -A && git commit -m "resolve merge conflicts"
```

## Part of the git toolkit

mergefix is part of a suite of AI-powered git tools:

| Tool | What it does |
|------|--------------|
| **[gitbrief](https://github.com/faw21/gitbrief)** | Pack your git history into LLM context |
| **[gpr](https://github.com/faw21/gpr)** | Generate PR descriptions and commit messages |
| **[critiq](https://github.com/faw21/critiq)** | AI code reviewer before you push |
| **[standup-ai](https://github.com/faw21/standup-ai)** | Generate daily standups from git history |
| **[changelog-ai](https://github.com/faw21/changelog-ai)** | Generate CHANGELOG from commits |
| **mergefix** | **Resolve merge conflicts with AI** |

## License

MIT
