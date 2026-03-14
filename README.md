# mergefix — AI Git Merge Conflict Resolver

AI-powered merge conflict resolver that uses Claude, OpenAI, or local Ollama to resolve git conflicts intelligently — preserving the intent of both sides.

```
$ mergefix
Scanning for conflicts…  Found 3 files with conflicts

  src/auth.py          2 conflicts
  config/settings.py   1 conflict
  tests/test_api.py    1 conflict

Resolving src/auth.py… ━━━━━━━━━━ 2/2 ✓
Resolving config/settings.py… ━━━━━━━━━━ 1/1 ✓
Resolving tests/test_api.py… ━━━━━━━━━━ 1/1 ✓

✅ All 4 conflicts resolved  (backups saved as .orig)
```

## Why mergefix?

Manual conflict resolution is tedious and error-prone. mergefix reads both sides of a conflict, understands the intent of each change, and produces a sensible merge — the same way an experienced developer would.

## Installation

```bash
pip install mergefix
```

Set your API key (or use Ollama for free local resolution):

```bash
export ANTHROPIC_API_KEY=your-key   # Claude (default, best quality)
export OPENAI_API_KEY=your-key      # or OpenAI
```

## Usage

```bash
# Resolve all conflicts in current repo
mergefix

# Resolve a specific file
mergefix src/auth.py

# Preview resolutions without writing (dry run)
mergefix --preview

# Apply without confirmation prompts
mergefix --yes

# Use local Ollama (no API key needed)
mergefix --provider ollama --model qwen2.5

# Use OpenAI
mergefix --provider openai --model gpt-4o

# No backup files
mergefix --no-backup
```

## Features

- **Intelligent merging** — understands the intent of both conflict sides, not just text diffing
- **Multi-file** — resolves all conflicted files in a repo in one command
- **Diff3 support** — handles 3-way conflicts with common ancestor
- **Multi-conflict** — handles files with multiple conflict blocks
- **Preview mode** — see what would change before writing (`--preview`)
- **Git context** — uses surrounding code as context for better resolutions
- **Exit codes** — `0` = success, `1` = partial failure, `2` = all failed (CI-friendly)
- **Backup** — saves `.orig` files before overwriting (disable with `--no-backup`)
- **Local LLM** — works with Ollama (qwen2.5, llama3.2, codellama)

## Providers

| Provider | Command | Quality |
|---|---|---|
| Claude (default) | `mergefix` | Best — understands intent |
| OpenAI | `mergefix --provider openai` | Good |
| Ollama (local, free) | `mergefix --provider ollama` | Decent |

## Ecosystem

Part of the AI developer workflow toolkit:

```
standup-ai      # 1. Morning: generate daily standup from git commits
critiq          # 2. Pre-commit: AI code review + auto-fix
gpr             # 3. Commit/PR: generate commit messages and PR descriptions
mergefix        # 4. Merge: resolve conflicts intelligently
gitbrief        # 5. Review: pack context for LLM PR review
changelog-ai    # 6. Release: generate CHANGELOG from commits
```

- [critiq](https://github.com/faw21/critiq) — AI code reviewer (pre-push)
- [gpr](https://github.com/faw21/gpr) — AI commit message + PR description generator
- [gitbrief](https://github.com/faw21/gitbrief) — Git-history-aware LLM context packer
- [standup-ai](https://github.com/faw21/standup-ai) — Daily standup generator
- [changelog-ai](https://github.com/faw21/changelog-ai) — AI changelog generator

## License

MIT — see [LICENSE](LICENSE)
