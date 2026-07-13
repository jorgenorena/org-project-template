#!/usr/bin/env bash
# Copies this template's rendering machinery on top of another repo (one
# that already tracks its own notes/, code/, algebra/, whatever), leaving
# that repo's existing content untouched, and installs .gitignore_alt as
# .gitignore there so the destination repo doesn't track the machinery.
set -euo pipefail

usage() {
    echo "Usage: $0 <destination-dir> [-y|--yes]" >&2
    exit 1
}

[ $# -ge 1 ] || usage

dest_arg="$1"
shift || true
assume_yes=0
for arg in "$@"; do
    case "$arg" in
        -y|--yes) assume_yes=1 ;;
        *) usage ;;
    esac
done

src_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -d "$dest_arg" ] || { echo "Destination '$dest_arg' does not exist." >&2; exit 1; }
dest_dir="$(cd "$dest_arg" && pwd)"
[ "$src_dir" != "$dest_dir" ] || { echo "Source and destination are the same directory." >&2; exit 1; }

# What is deliberately NOT copied:
#   .git                      version control state.
#   notes                     this template's own example notes; the
#                             destination keeps whatever it already has.
#   .gitignore/.gitignore_alt handled separately below (installed as the
#                             destination's .gitignore, not copied verbatim).
#   agent files               AI-assistant context that only makes sense in
#                             this template (.claude, .codex, .cursor,
#                             AGENT.md, AGENTS.md, CLAUDE.md, GEMINI.md, ...).
#   Python project files      packaging/env/cache, never the machinery itself
#                             (the *.py scripts ARE the machinery and are
#                             copied): __pycache__, *.egg-info, .venv, venv,
#                             pyproject.toml, setup.py/cfg, requirements*.txt,
#                             Pipfile*, poetry.lock, uv.lock, .python-version,
#                             .mypy_cache, .ruff_cache, .pytest_cache, .tox.
#   readme/docs               README* and docs/; the destination documents
#                             itself.
shopt -s dotglob nullglob
entries=()
for entry in "$src_dir"/*; do
    name="$(basename "$entry")"
    case "$name" in
        # version control, example notes, gitignore (handled below)
        .git|notes|.gitignore|.gitignore_alt) continue ;;
        # agent / AI-assistant files
        .claude|.codex|.cursor|.cursorrules|.aider*) continue ;;
        AGENT.md|AGENTS.md|CLAUDE.md|GEMINI.md|.clauderc) continue ;;
        # Python project files (not the *.py machinery scripts)
        __pycache__|*.egg-info|.venv|venv|env|.tox) continue ;;
        pyproject.toml|setup.py|setup.cfg|requirements*.txt) continue ;;
        Pipfile|Pipfile.lock|poetry.lock|uv.lock|.python-version) continue ;;
        .mypy_cache|.ruff_cache|.pytest_cache) continue ;;
        # readme / docs
        README*|docs) continue ;;
    esac
    entries+=("$entry")
done

echo "Will copy into '$dest_dir':"
for entry in "${entries[@]}" "$src_dir/.gitignore_alt"; do
    name="$(basename "$entry")"
    [ "$name" = ".gitignore_alt" ] && name=".gitignore"
    if [ -e "$dest_dir/$name" ]; then
        echo "  $name (overwrites existing)"
    else
        echo "  $name"
    fi
done

if [ "$assume_yes" -ne 1 ]; then
    read -r -p "Proceed? [y/N] " reply
    case "$reply" in
        y|Y|yes|YES) ;;
        *) echo "Aborted."; exit 1 ;;
    esac
fi

for entry in "${entries[@]}"; do
    cp -a "$entry" "$dest_dir/"
done
cp -a "$src_dir/.gitignore_alt" "$dest_dir/.gitignore"

echo "Done."
