# Research Notes Site

This repository builds a static website from research notes written in either
Org mode or LaTeX. It also collects a coherent LaTeX version of the notes:
Org notes are exported to `.tex`, while hand-written `.tex` notes are copied as
source files.

The build stays deliberately small. Emacs handles Org export, pandoc handles
LaTeX-to-HTML fragments, and `build_site.py` wraps those fragments with plain
HTML templates. The machinery can also be dropped on top of an existing
repository that already has its own notes (see
[Reusing the Machinery](#reusing-the-machinery-in-another-repo)).

## What It Produces

- `public/`: the generated static website.
- `build/`: intermediate body-only HTML fragments.
- `build/latex/`: collected LaTeX for every note.

The path layout is mirrored from `notes/` through to `public/`:

```text
notes/foo.org      -> build/foo.html      -> public/foo.html
notes/bar.tex      -> build/bar.html      -> public/bar.html
notes/sub/baz.org  -> build/sub/baz.html  -> public/sub/baz.html
```

Everything under `build/` and `public/` is disposable and regenerated on each
build.

## Dependencies

Always required:

- Python 3 with `PyYAML`.
- `just`, used as the command runner.

For Org notes (`.org`):

- Emacs with Org export support, plus the `htmlize` package for source
  highlighting.
- Org export runs through a **running Emacs server** (start one with
  `emacs --daemon`, or `M-x server-start` inside a running Emacs). If a project
  has no `.org` notes, Emacs is not needed and the Org step is skipped
  automatically. If it has `.org` notes but no server is reachable, the build
  stops with a clear error instead of producing a half-built site.

For LaTeX notes (`.tex`):

- `pandoc`, used to convert `.tex` notes to body-only HTML fragments.

Optional:

- A TeX distribution such as TeX Live (`pdflatex`) if you want to compile PDFs
  directly from the collected LaTeX.

No Node or frontend build step is required. Browser assets such as MathJax and
fonts are vendored under `site/static/vendor/`.

## Quick Start

Put notes in `notes/`.

For an Org note:

```org
#+TITLE: My note
#+DESCRIPTION: Short description for the index

* First section
```

For a LaTeX note:

```latex
%+TITLE: My LaTeX note
%+DESCRIPTION: Short description for the index
\documentclass{article}

\begin{document}
\section{First section}
\end{document}
```

Build everything:

```sh
just quick
```

Build and serve locally:

```sh
just site
```

Serve an existing build:

```sh
just serve
```

Generate the collected LaTeX output:

```sh
just latex
```

Clean generated output:

```sh
just clean
```

Run `just` to list all recipes.

## Commands

- `just fragments`: export Org notes to HTML fragments with Emacs. Skips
  Emacs when there are no `.org` notes; fails with a clear message if there
  are `.org` notes but no Emacs server is running.
- `just tex-fragments`: export LaTeX notes to HTML fragments with pandoc.
- `just build`: build `public/` from existing fragments.
- `just quick`: run Org export, LaTeX export, then the site build.
- `just latex`: export Org notes to LaTeX and copy hand-written `.tex` notes
  into `build/latex/`. The Emacs step is skipped (not failed) for `.tex`-only
  projects, so they still collect their LaTeX.
- `just site [port]`: build and serve the site, defaulting to port `8000`.
- `just serve [port]`: serve the existing `public/` directory.
- `just serve-static [port]`: serve with Python's plain static server.
- `just clean`: remove generated directories.

While `just site` or `just serve` is running, press `Ctrl+R` in that terminal
to run `just quick` again. Press `Ctrl+C` to stop the server.

## Writing Notes

Every note needs a `TITLE` metadata line. `DESCRIPTION` is optional but used
for the index cards. Org metadata uses `#+KEY: value`; LaTeX metadata uses
`%+KEY: value` and must appear before `\documentclass`.

The builder reads only `TITLE` and `DESCRIPTION` from a note. Menu **grouping**
and **order** are controlled in `site.yml` (see
[Menu Order](#menu-order) and [Subfolders and Submenus](#subfolders-and-submenus)),
not through per-note metadata.

Do not create both `notes/foo.org` and `notes/foo.tex`: they both generate
`foo.html`, and the builder treats that clash as an error.

Use ordinary relative links for figures and generated files. Asset directories
are copied according to `site.yml`; by default this includes:

- `site/static/` -> `public/static/`
- `notes/figures/` -> `public/figures/`
- `results/` -> `public/results/`
- `algebra/` -> `public/algebra/`

After generating the site, the builder validates every local `href` and `src`
link and fails if any point to a missing file.

### Admonition blocks

Special blocks are styled by the site CSS. In Org, use
`#+begin_info ... #+end_info` (and likewise `warning`, `theorem`, `definition`,
`proof`, `note`, `tip`). In LaTeX the same names work as environments
(`\begin{info} ... \end{info}`), since pandoc turns an unknown environment
`X` into `<div class="X">`.

### Transclusion (Org)

An Org note can inline another whole Org file before export:

```org
#+transclude: [[file:shared/preamble.org]]
```

Transclusions are expanded recursively (cycles are detected and rejected).
Only whole-file links are supported, not search targets.

## Menu Order

By default notes are listed alphabetically. To control the order, list note
slugs under `notes.order` in `site.yml`. A slug is a note's path under
`notes/` without the `.org`/`.tex` extension:

```yml
notes:
  root: notes
  order:
    - intro
    - flrw-background
    - cosmology/perturbations   # a note inside a section subfolder
```

Listed notes appear first, in this order; any note not listed follows
alphabetically. The order applies within each group, so it ranks both the
top-level notes and the notes inside each section. A stale entry (a slug that
matches no note) is reported as a warning and otherwise ignored, so the build
never breaks just because a note was renamed or removed.

## Subfolders and Submenus

Notes placed directly in `notes/` appear as a flat list in the site menu. To
organize notes into subfolders and show each as its own submenu, list the
subfolders under `notes.sections` in `site.yml`:

```yml
notes:
  root: notes
  sections:
    - dir: cosmology
      title: Cosmology
    - algebra           # bare name; the submenu title is the folder name
```

Only the subfolders listed here are scanned for notes (recursively). Any other
subfolder — for example `notes/figures/` — is treated as assets and left
alone, so asset directories are never rendered as pages. Each listed section
becomes a titled submenu in the global site menu, below the top-level notes.

## LaTeX Notes

LaTeX notes are converted with pandoc using body-only HTML output and MathJax
math. Section headings are shifted down one level so the page template owns the
single visible `<h1>`.

Reusable macros should usually live in `site/latex/macros.tex` and be included
from notes with `\input`. Plain `\newcommand` definitions are expanded by
pandoc during HTML conversion, so MathJax does not need duplicate definitions.

For direct PDF builds of a hand-written note, compile from the note directory
so relative `\input` and figure paths resolve naturally:

```sh
cd notes
pdflatex example_latex.tex
```

## Citations and Bibliography

Org notes use Org's native citations with a BibTeX file and a CSL style:

```org
#+BIBLIOGRAPHY: ../references/references.bib
#+CITE_EXPORT: csl ../site/csl/myrefs.csl

#+PRINT_BIBLIOGRAPHY:
```

Keep your `.bib` files (and papers) under `references/`. The CSL citation
style ships with the machinery under `site/csl/`. Citations are formatted by
Emacs during Org export; the builder does not touch them.

## Configuration

`site.yml` is the single source of truth for paths, templates, copied assets,
and site metadata:

- `site.title`: site name shown in the header.
- `site.output`: final website directory (default `public`).
- `notes.root`: source note directory.
- `notes.public_prefix`: optional path prefix for notes under the output
  directory (empty by default).
- `notes.order`: explicit menu order for notes (see [Menu Order](#menu-order)).
- `notes.sections`: subfolders rendered as submenus (see
  [Subfolders and Submenus](#subfolders-and-submenus)).
- `fragments.root`: intermediate HTML fragment directory (default `build`).
- `latex.root`: collected LaTeX output directory (default `build/latex`).
- `latex.header`: shared LaTeX preamble added to Org-exported `.tex`.
- `templates.page` and `templates.index`: HTML templates.
- `assets`: directory copy rules (`from` -> `to`) for static files, figures,
  and results.
- `index.title` and `index.description`: metadata for the index page.

Generated directories are disposable. Edit notes, templates, CSS, JavaScript,
and `site.yml`; rebuild outputs with `just quick` or `just latex`.

## Reusing the Machinery in Another Repo

`sync_to_notes_repo.sh` copies this template's rendering machinery on top of
another repository that already tracks its own content (its own `notes/`, and
maybe `code/`, `algebra/`, and so on), so that repo can build the same site
without vendoring a copy by hand:

```sh
./sync_to_notes_repo.sh /path/to/destination        # shows a plan, then asks
./sync_to_notes_repo.sh /path/to/destination -y      # skip the confirmation
```

It copies the builder scripts (`build_site.py`, `export_tex.py`,
`export-fragments.el`, `serve_site.py`) and the `site/` directory (templates,
CSS, JS, LaTeX includes, and the CSL style). It also installs `.gitignore_alt`
as the destination's `.gitignore`, so the machinery stays untracked there while
the destination keeps tracking its own content.

It deliberately does **not** copy:

- version control state (`.git`) and this template's example `notes/` and
  `references/` — the destination keeps its own;
- agent / assistant files (`.claude`, `AGENT.md`, `CLAUDE.md`, ...);
- Python project files (`pyproject.toml`, `.venv`, caches, ...) — though the
  `*.py` builder scripts themselves are copied;
- `README*` and `docs/` — the destination documents itself.

Site-local files that the destination owns — `site.yml` and `justfile` — are
copied only if they are **missing**, so re-running the script to pick up
machinery updates never clobbers the destination's own configuration.
