#!/usr/bin/env python3
"""Export hand-written LaTeX notes for the static site.

Two responsibilities, mirroring the Org toolchain:

    fragments   notes/**/*.tex -> build/**/*.html        (via pandoc, body-only)
    latex       notes/**/*.tex -> build/latex/**/*.tex    (verbatim copy)

The HTML fragments are body-only and land in the same place the Org exporter
writes to, so ``build_site.py`` wraps them into pages without caring whether a
note came from Org or LaTeX.

Conversion notes:

- Math is left as raw TeX for MathJax (``--mathjax``).
- ``\\newcommand`` macros are expanded by pandoc, so MathJax never needs them.
- Headings are shifted down one level (``--shift-heading-level-by=1``) so
  ``\\section`` becomes ``<h2>``, matching Org notes and the section nav.
- ``\\begin{info}...\\end{info}`` becomes ``<div class="info">`` automatically.
- pandoc runs with the note's own directory as the working directory, so
  ``\\input`` and ``\\includegraphics`` resolve the way pdflatex would when the
  note is compiled in place.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "site.yml"

PANDOC_ARGS = [
    "--from=latex",
    "--to=html5",
    "--mathjax",
    "--shift-heading-level-by=1",
]


def fail(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")


def resolve_path(raw: dict, section: str, key: str, default: str) -> Path:
    value = (raw.get(section) or {}).get(key, default)
    if not isinstance(value, str) or not value:
        fail(f"site.yml field {section}.{key} must be a non-empty path string")
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def load_paths() -> tuple[Path, Path, Path]:
    if not CONFIG_PATH.exists():
        fail(f"missing site configuration: {CONFIG_PATH}")
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        fail(f"{CONFIG_PATH} must contain a YAML mapping")

    notes_dir = resolve_path(raw, "notes", "root", "notes")
    fragments_dir = resolve_path(raw, "fragments", "root", "build")
    latex_dir = resolve_path(raw, "latex", "root", "build/latex")
    return notes_dir, fragments_dir, latex_dir


def tex_notes(notes_dir: Path) -> list[Path]:
    if not notes_dir.is_dir():
        fail(f"notes directory does not exist: {notes_dir}")
    return sorted(notes_dir.rglob("*.tex"))


def export_fragment(note: Path, notes_dir: Path, fragments_dir: Path) -> None:
    out_file = fragments_dir / note.relative_to(notes_dir).with_suffix(".html")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    print(f"pandoc {note} -> {out_file}")

    result = subprocess.run(
        ["pandoc", note.name, *PANDOC_ARGS, "-o", str(out_file)],
        cwd=note.parent,
        capture_output=True,
        text=True,
    )
    if result.stderr.strip():
        sys.stderr.write(result.stderr)
    if result.returncode != 0:
        fail(f"pandoc failed on {note} (exit {result.returncode})")


def copy_latex(note: Path, notes_dir: Path, latex_dir: Path) -> None:
    out_file = latex_dir / note.relative_to(notes_dir)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    print(f"copy {note} -> {out_file}")
    shutil.copy2(note, out_file)


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "fragments"
    if mode not in {"fragments", "latex"}:
        fail(f"unknown mode: {mode!r} (expected 'fragments' or 'latex')")

    notes_dir, fragments_dir, latex_dir = load_paths()
    notes = tex_notes(notes_dir)

    if not notes:
        print(f"No .tex notes found in {notes_dir}; nothing to do.")
        return

    if mode == "fragments":
        if shutil.which("pandoc") is None:
            fail("pandoc not found on PATH; install pandoc to export LaTeX notes")
        for note in notes:
            export_fragment(note, notes_dir, fragments_dir)
        print(f"Exported {len(notes)} LaTeX note(s) to HTML fragments.")
    else:
        for note in notes:
            copy_latex(note, notes_dir, latex_dir)
        print(f"Copied {len(notes)} LaTeX note(s) into {latex_dir}.")


if __name__ == "__main__":
    main()
