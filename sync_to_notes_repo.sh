#!/usr/bin/env bash
# Copies this template's rendering machinery on top of another repo (one
# that already tracks its own notes/, code/, algebra/, whatever), leaving
# that repo's existing content untouched, and merges .gitignore_alt into the
# destination's .gitignore so that repo doesn't track the machinery.
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

# Site-local files: configuration the destination repo owns and customizes.
# They are copied only when the destination doesn't already have one, so
# re-running this script to update the machinery never clobbers the
# destination's own site.yml / justfile.
site_local="site.yml justfile"

is_site_local() {
    local candidate="$1" name
    for name in $site_local; do
        [ "$name" = "$candidate" ] && return 0
    done
    return 1
}

# The machinery's ignore rules live in .gitignore_alt between these markers.
# Rather than overwrite the destination's .gitignore, we replace our own block
# in place (or append it the first time), so the destination's own rules survive
# every re-sync, keep their position relative to ours, and stale machinery rules
# never pile up.
gitignore_begin="# >>> org-project-template machinery (managed by sync_to_notes_repo.sh) >>>"
gitignore_end="# <<< org-project-template machinery <<<"

merge_gitignore() {
    local dest="$dest_dir/.gitignore"
    if [ ! -f "$dest" ]; then
        cp -a "$src_dir/.gitignore_alt" "$dest"
        echo "wrote .gitignore"
        return
    fi

    # A begin without its end (hand-edited away) would make the awk below skip
    # to end-of-file, so refuse rather than silently destroy their rules.
    local begins ends
    begins="$(grep -cxF -- "$gitignore_begin" "$dest" || true)"
    ends="$(grep -cxF -- "$gitignore_end" "$dest" || true)"
    if [ "$begins" != "$ends" ]; then
        echo "ERROR: $dest has unbalanced machinery markers ($begins begin, $ends end)." >&2
        echo "Fix them by hand (or delete the whole block) and re-run." >&2
        exit 1
    fi

    if [ "$begins" -gt 1 ]; then
        echo "ERROR: $dest has $begins machinery blocks; this script only ever writes one." >&2
        echo "Delete the extras by hand and re-run." >&2
        exit 1
    fi

    local tmp
    tmp="$(mktemp)"
    if [ "$begins" -eq 1 ]; then
        # Swap the old block for the new one *where it already sits*. Order
        # matters in .gitignore (a later '!rule' overrides an earlier ignore),
        # so moving their rules relative to ours could silently change meaning.
        awk -v b="$gitignore_begin" -v e="$gitignore_end" -v f="$src_dir/.gitignore_alt" '
            BEGIN { while ((getline line < f) > 0) block = block line "\n" }
            $0 == b { skip = 1; printf "%s", block; next }
            $0 == e { skip = 0; next }
            !skip
        ' "$dest" > "$tmp"
        echo "refreshed the machinery block in .gitignore"
    else
        # No block yet: append one, separated from their rules by a blank line.
        # The command substitution trims any trailing blank lines they had.
        local kept
        kept="$(cat "$dest")"
        {
            [ -n "$kept" ] && printf '%s\n\n' "$kept"
            cat "$src_dir/.gitignore_alt"
        } > "$tmp"
        echo "appended the machinery block to .gitignore"
    fi
    cat "$tmp" > "$dest"
    rm -f "$tmp"
}

# What is deliberately NOT copied:
#   .git                      version control state.
#   notes                     this template's own example notes; the
#                             destination keeps whatever it already has.
#   references                the destination's own bibliography and papers
#                             (.bib, PDFs). The CSL citation *style* is
#                             machinery and ships under site/csl/, which IS
#                             copied as part of site/.
#   .gitignore/.gitignore_alt handled separately below (merged into the
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
        # version control, example content, gitignore (handled below)
        .git|notes|references|.gitignore|.gitignore_alt) continue ;;
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
for entry in "${entries[@]}"; do
    name="$(basename "$entry")"
    if [ -e "$dest_dir/$name" ]; then
        if is_site_local "$name"; then
            echo "  $name (kept; destination already has one)"
        else
            echo "  $name (overwrites existing)"
        fi
    else
        echo "  $name"
    fi
done
if [ -f "$dest_dir/.gitignore" ]; then
    echo "  .gitignore (merged; your own rules kept)"
else
    echo "  .gitignore"
fi

if [ "$assume_yes" -ne 1 ]; then
    read -r -p "Proceed? [y/N] " reply
    case "$reply" in
        y|Y|yes|YES) ;;
        *) echo "Aborted."; exit 1 ;;
    esac
fi

for entry in "${entries[@]}"; do
    name="$(basename "$entry")"
    if is_site_local "$name" && [ -e "$dest_dir/$name" ]; then
        echo "keeping existing $name"
        continue
    fi
    cp -a "$entry" "$dest_dir/"
done
merge_gitignore

echo "Done."
