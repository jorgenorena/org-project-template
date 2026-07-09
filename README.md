# Research Notes Site

This repository builds a static website from research notes written in either
Org mode or LaTeX. It also collects a coherent LaTeX version of the notes:
Org notes are exported to `.tex`, while hand-written `.tex` notes are copied as
source files.

The build stays deliberately small. Emacs handles Org export, pandoc handles
LaTeX-to-HTML fragments, and `build_site.py` wraps those fragments with plain
HTML templates.

## What It Produces

- `public/`: the generated static website.
- `build/`: intermediate body-only HTML fragments.
- `build/latex/`: LaTeX output for all notes.

The path layout is mirrored:

```text
notes/foo.org      -> build/foo.html      -> public/foo.html
notes/bar.tex      -> build/bar.html      -> public/bar.html
notes/sub/baz.org  -> build/sub/baz.html  -> public/sub/baz.html
```

## Dependencies

Required:

- Python 3 with `PyYAML`.
- `just`, used as the command runner.
- Emacs with Org export support.
- `htmlize`, used by Org HTML export for source highlighting.
- `pandoc`, used to convert `.tex` notes to HTML fragments.

Optional:

- A TeX distribution such as TeX Live if you want to compile PDFs directly.
- `pdflatex` for hand-written `.tex` notes and generated Org LaTeX.

The Org recipes call `emacsclient`, so start an Emacs server before running
`just quick`, `just site`, or `just latex`. No Node or frontend build step is
required. Browser assets such as MathJax and fonts are vendored under
`site/static/vendor/`.

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

- `just fragments`: export Org notes to HTML fragments with Emacs.
- `just tex-fragments`: export LaTeX notes to HTML fragments with pandoc.
- `just build`: build `public/` from existing fragments.
- `just quick`: run Org export, LaTeX export, then site build.
- `just latex`: export Org notes to LaTeX and copy hand-written `.tex` notes.
- `just site [port]`: build and serve the site, defaulting to port `8000`.
- `just serve [port]`: serve the existing `public/` directory.
- `just serve-static [port]`: serve with Python's plain static server.
- `just clean`: remove generated directories.

While `just site` or `just serve` is running, press `Ctrl+R` in that terminal to
run `just quick` again. Press `Ctrl+C` to stop the server.

## Writing Notes

Every note needs a `TITLE` metadata line. `DESCRIPTION` is optional but useful
for the index page.

Org metadata uses `#+KEY: value`; LaTeX metadata uses `%+KEY: value`. LaTeX
metadata must appear before `\documentclass`.

Do not create both `notes/foo.org` and `notes/foo.tex`: they both generate
`foo.html`, and the builder treats that as an error.

Use ordinary relative links for figures and generated files. Asset directories
are copied according to `site.yml`; by default this includes:

- `site/static/` -> `public/static/`
- `notes/figures/` -> `public/figures/`
- `results/` -> `public/results/`
- `algebra/` -> `public/algebra/`

The builder validates local `href` and `src` links after generating the site.

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

## Configuration

`site.yml` is the source of truth for paths, templates, copied assets, and site
metadata. The most important fields are:

- `site.output`: final website directory.
- `notes.root`: source note directory.
- `fragments.root`: intermediate HTML fragment directory.
- `latex.root`: collected LaTeX output directory.
- `templates.page` and `templates.index`: HTML templates.
- `assets`: directory copy rules for static files, figures, and results.

Generated directories are disposable. Edit notes, templates, CSS, JavaScript,
and `site.yml`; rebuild outputs with `just quick` or `just latex`.
