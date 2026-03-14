"""
mergefix CLI — AI-powered git merge conflict resolver.

Usage:
    mergefix                          # resolve all conflicted files in cwd
    mergefix src/auth.py              # resolve a specific file
    mergefix --dry-run                # show resolutions without writing
    mergefix --provider ollama        # use local Ollama (free, no API key)
"""

from __future__ import annotations

import difflib
import shutil
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from . import __version__
from .parser import ParsedFile, apply_resolutions, find_conflict_files, parse_file
from .providers import resolve_conflict
from .resolver import build_prompt, clean_response

console = Console()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _show_diff(original: str, resolved: str, filename: str) -> None:
    """Print a colorized unified diff between original and resolved content."""
    orig_lines = original.splitlines(keepends=True)
    new_lines = resolved.splitlines(keepends=True)
    diff = list(
        difflib.unified_diff(
            orig_lines,
            new_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            n=3,
        )
    )
    if diff:
        diff_text = "".join(diff)
        console.print(Syntax(diff_text, "diff", theme="monokai"))
    else:
        console.print("[dim]  (no visible changes)[/dim]")


def _guess_language(path: Path) -> str:
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".rb": "ruby",
        ".cpp": "cpp",
        ".c": "c",
        ".cs": "csharp",
        ".swift": "swift",
        ".kt": "kotlin",
        ".md": "markdown",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".json": "json",
        ".sh": "bash",
        ".html": "html",
        ".css": "css",
    }
    return ext_map.get(path.suffix.lower(), "text")


def _resolve_single_file(
    path: Path,
    provider_name: str,
    model: str | None,
    dry_run: bool,
    backup: bool,
    auto_apply: bool,
) -> bool:
    """
    Process one file. Returns True if fully resolved.
    """
    content = path.read_text(encoding="utf-8")
    parsed = parse_file(content, path)

    if not parsed.has_conflicts:
        console.print(f"[dim]{path}: no conflicts[/dim]")
        return True

    rel_path = str(path.relative_to(Path.cwd())) if path.is_relative_to(Path.cwd()) else str(path)
    console.print(
        f"\n[bold cyan]→ {rel_path}[/bold cyan] "
        f"[dim]({parsed.conflict_count} conflict{'' if parsed.conflict_count == 1 else 's'})[/dim]"
    )

    file_ext = path.suffix.lower()
    resolutions: list[str] = []
    all_ok = True

    for i, conflict in enumerate(parsed.conflicts, 1):
        label = f"Conflict {i}/{len(parsed.conflicts)}"
        prompt = build_prompt(conflict, file_ext)

        with console.status(f"Resolving {label} with AI…"):
            try:
                raw = resolve_conflict(prompt, provider_name, model)
                resolution = clean_response(raw)
                if not resolution.endswith("\n"):
                    resolution += "\n"
                resolutions.append(resolution)
            except Exception as exc:
                console.print(f"  [red]✗ {label}: {exc}[/red]")
                all_ok = False
                resolutions.append("")
                continue

        console.print(f"\n  [bold]{label}[/bold]")
        console.print(f"  [dim]ours: {conflict.ours_label[:50]}[/dim]")
        console.print(f"  [dim]theirs: {conflict.theirs_label[:50]}[/dim]")

        console.print("  [green]✓ Resolution:[/green]")
        if resolution.strip():
            console.print(
                Syntax(
                    resolution,
                    _guess_language(path),
                    theme="monokai",
                    background_color="default",
                )
            )
        else:
            console.print("  [dim](empty — both sides deleted this section)[/dim]")

    if not all_ok:
        return False

    if dry_run:
        console.print("\n[yellow]Dry-run mode — not writing changes.[/yellow]")
        return True

    # Show full diff before writing
    resolved_content = apply_resolutions(parsed.original_content, parsed.conflicts, resolutions)

    console.print("\n[bold]Diff:[/bold]")
    _show_diff(parsed.original_content, resolved_content, rel_path)

    if not auto_apply:
        apply = click.confirm(f"\n  Apply resolutions to {rel_path}?", default=True)
        if not apply:
            console.print("[dim]  Skipped.[/dim]")
            return False

    if backup:
        backup_path = parsed.path.with_suffix(parsed.path.suffix + ".orig")
        shutil.copy2(parsed.path, backup_path)

    parsed.path.write_text(resolved_content, encoding="utf-8")
    backup_note = " (backup: .orig)" if backup else ""
    console.print(f"  [green]✓ Applied{backup_note}[/green]")
    return True


# ── CLI ───────────────────────────────────────────────────────────────────────

@click.command()
@click.version_option(__version__)
@click.argument("files", nargs=-1, type=click.Path(exists=True))
@click.option(
    "--provider",
    "-p",
    default="claude",
    type=click.Choice(["claude", "openai", "ollama"]),
    show_default=True,
    help="LLM provider.",
)
@click.option("--model", "-m", default=None, help="Model override.")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show resolutions without writing to files.",
)
@click.option(
    "--auto",
    is_flag=True,
    help="Apply all resolutions without prompting.",
)
@click.option(
    "--backup",
    is_flag=True,
    help="Keep original files as .orig before overwriting.",
)
@click.option(
    "--context",
    default=None,
    help="Extra context for the AI (e.g. 'This is a Python web app, prefer async patterns').",
)
def main(
    files: tuple[str, ...],
    provider: str,
    model: str | None,
    dry_run: bool,
    auto: bool,
    backup: bool,
    context: str | None,
) -> None:
    """
    Resolve git merge conflicts using AI.

    With no arguments, finds all conflicted files in the current directory.
    Pass specific files to resolve only those.

      mergefix                         # resolve all conflicts in cwd
      mergefix src/auth.py             # resolve one file
      mergefix --dry-run               # show resolutions without writing
      mergefix --auto                  # auto-apply (no prompts)
      mergefix --provider ollama       # use local model (free)
    """
    cwd = Path.cwd()

    if files:
        target_files = [Path(f) for f in files]
    else:
        with console.status("Scanning for conflict markers…"):
            target_files = find_conflict_files(cwd)

    if not target_files:
        console.print("[green]✅ Found no conflicts — nothing to resolve.[/green]")
        sys.exit(0)

    total_conflict_count = 0
    conflicted_files: list[Path] = []
    for f in target_files:
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            if "<<<<<<< " in content:
                parsed = parse_file(content, f)
                total_conflict_count += parsed.conflict_count
                conflicted_files.append(f)
        except Exception:
            pass

    if total_conflict_count == 0:
        console.print("[green]✅ Found no conflicts — nothing to resolve.[/green]")
        sys.exit(0)

    console.print(
        Panel(
            Text.from_markup(
                f"[bold]mergefix[/bold]  ·  "
                f"[cyan]{len(target_files)} file{'' if len(target_files) == 1 else 's'}[/cyan]  ·  "
                f"[yellow]{total_conflict_count} conflict{'' if total_conflict_count == 1 else 's'}[/yellow]  ·  "
                f"provider: [magenta]{provider}[/magenta]"
            ),
            border_style="blue",
        )
    )

    resolved_files = 0
    failed_files = 0

    for f in target_files:
        try:
            ok = _resolve_single_file(
                path=f,
                provider_name=provider,
                model=model,
                dry_run=dry_run,
                backup=backup,
                auto_apply=auto,
            )
            if ok:
                resolved_files += 1
            else:
                failed_files += 1
        except Exception as exc:
            console.print(f"[red]✗ {f}: {exc}[/red]")
            failed_files += 1

    console.print()
    if failed_files == 0:
        console.print(
            f"[bold green]✅ All {resolved_files} file(s) resolved.[/bold green]"
        )
        if not dry_run:
            console.print("[dim]Run `git diff` to review changes, then `git add` to mark as resolved.[/dim]")
    else:
        console.print(
            f"[yellow]⚠️  {resolved_files} resolved, {failed_files} failed.[/yellow]"
        )
        sys.exit(1)
