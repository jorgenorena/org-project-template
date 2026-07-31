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
and **order** are controlled in `site.yml` (see [The Menu](#the-menu)), not
through per-note metadata.

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

During HTML fragment export, local image URLs receive a query parameter derived
from the first 12 hexadecimal characters of the image's SHA-256 digest, for
example `figures/plot.png?v=8c21bd17c122`. Changing the image changes its URL,
so a browser showing the live preview requests the new version immediately.
External and missing image URLs are left unchanged.

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

## The Menu

The site menu is described by one list, `notes.menu`, written in the order it
renders. There is no separate grouping and ordering setting: the config reads
top-to-bottom exactly like the menu it produces.

```yml
notes:
  root: notes
  menu:
    - intro                    # a top-level note
    - flrw-background
    - dir: cosmology           # a subfolder, as its own submenu
      title: Cosmology         # optional; defaults to the folder name
      notes:                   # optional; may be partial
        - perturbations
    - algebra                  # a bare folder name works too
```

An entry is one of:

- **A note slug** — the note's path under `notes/` without the `.org`/`.tex`
  extension (`intro`, or `cosmology/perturbations` to pull one note out of its
  folder and show it at the top level). A trailing extension is accepted and
  stripped.
- **A subfolder**, either as a bare folder name or as a `dir:` mapping. Use the
  mapping to set the submenu `title:`, or to order the notes inside it with
  `notes:`. Those inner entries read relative to the folder
  (`perturbations`), though a full slug works too. Subfolders are scanned
  recursively.

A bare entry is resolved by looking at the filesystem: if a note of that name
exists it is a note, otherwise it is a subfolder. Consecutive note entries
render as one ungrouped block, so notes and submenus can be interleaved freely.

### What happens to anything you leave out

Listing is never mandatory — the menu is a set of preferences layered on a
sensible default, so a partial list (or no list at all) still shows every note.

- **An unlisted note in a listed subfolder** is appended alphabetically after
  that submenu's listed notes.
- **An unlisted top-level note** is appended alphabetically at the very end of
  the menu. So an empty `menu:` simply lists every top-level note
  alphabetically.
- **Every note appears exactly once**, in the first place that mentions it. If
  you promote `cosmology/perturbations` to the top level, it is not repeated
  inside the Cosmology submenu.
- **An unlisted subfolder is never scanned at all.** This is what keeps
  `notes/figures/` and other asset directories from being rendered as pages,
  and it is the one case where leaving something out really does hide it. To
  make that hard to do by accident, the build prints a warning naming any
  subfolder that contains notes but is not in the menu.

### Errors versus warnings

A `dir:` entry is an explicit structural claim, so pointing it at a folder that
does not exist stops the build. Everything else about the menu is best-effort
and only warns — a slug matching no note, or the same note listed twice — so
renaming or deleting a note never breaks the build, but you still hear about
the stale entry.

## LaTeX Notes

LaTeX notes are converted with pandoc using body-only HTML output and MathJax
math. Section headings are shifted down one level so the page template owns the
single visible `<h1>`.

Reusable macros should usually live in `site/latex/macros.tex` and be included
from notes with `\input`. Plain `\newcommand` definitions are expanded by
pandoc during HTML conversion, so MathJax does not need duplicate definitions.
The file also provides `\concept{...}`, whose site color follows the selected
theme (and has a matching fixed color in PDFs).

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
- `notes.menu`: the site menu — note order and subfolder submenus in one list
  (see [The Menu](#the-menu)).
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
CSS, JS, LaTeX includes, and the CSL style). It also keeps the destination's
`.gitignore` in sync: the machinery's ignore rules live in `.gitignore_alt`
between clearly marked `# >>> ... >>>` / `# <<< ... <<<` lines, and the script
**merges** just that block into the destination's `.gitignore` — replacing any
previous copy in place and leaving every rule you wrote outside the markers
untouched. So the machinery stays untracked, your own ignore rules survive each
re-sync, and stale machinery rules don't pile up. (If a repo has never been
synced, the script simply writes `.gitignore_alt` as its `.gitignore`.)

For agent instructions in a destination notes repo, the sync script extracts the managed block from `downstream-agent-block.md` and merges it into that repo's root `AGENT.md`. Existing destination-specific agent instructions outside the managed block are preserved; later syncs replace only the managed block. The block is written to root `AGENT.md`, not left in a sidecar file that agents may not read.

It deliberately does **not** copy:

- version control state (`.git`) and this template's example `notes/` and
  `references/` — the destination keeps its own;
- this template's agent / assistant files (`.claude`, `AGENT.md`, `CLAUDE.md`, ...) are not copied verbatim; only the managed notes-site block is merged into the destination's `AGENT.md`;
- Python project files (`pyproject.toml`, `.venv`, caches, ...) — though the
  `*.py` builder scripts themselves are copied;
- `README*` and `docs/` — the destination documents itself.

Site-local files that the destination owns — `site.yml` and `justfile` — are
copied only if they are **missing**, so re-running the script to pick up
machinery updates never clobbers the destination's own configuration.
