# Advanced Cosmology Notes Site

This project builds a static website from Org-mode notes. Individual notes can also be written directly in LaTeX.

The build has two stages:

1. Each note is exported to a body-only HTML fragment. `export-fragments.el` handles `.org` notes; `export_tex.py` (pandoc) handles `.tex` notes.
2. `build_site.py` wraps those fragments with HTML templates, builds the index and navigation, copies assets, and validates local links.

The intended data flow is the same for both formats:

```text
notes/foo.org             notes/bar.tex
  -> build/foo.html         -> build/bar.html
  -> public/foo.html        -> public/bar.html
```

Nested notes keep the same relative path:

```text
notes/project/baz.org
  -> build/project/baz.html
  -> public/project/baz.html
```

Everything after the fragment stage is format-agnostic, so Org and LaTeX notes share the same index, navigation, theme, MathJax, and link validation.

## Files

- `site.yml` defines the site architecture: source paths, fragment paths, output paths, templates, copied assets, and index metadata.
- `export-fragments.el` is the Emacs/Org exporter. It reads `notes.root` and `fragments.root` from `site.yml`.
- `export_tex.py` is the LaTeX exporter. It runs pandoc to convert `.tex` notes into the same body-only fragments, and can also copy `.tex` sources into `latex.root`.
- `build_site.py` is the static-site builder. It reads `site.yml`, loads note metadata from Org and LaTeX headers, wraps fragments with templates, copies assets, and checks links.
- `site/latex/` holds shared LaTeX pieces: `header.tex` (preamble injected into Org's LaTeX export) and `macros.tex` (macros shared by LaTeX notes and their PDFs).
- `site/templates/` contains plain HTML templates with `{{ placeholder }}` replacement.
- `site/static/` contains CSS, JavaScript, and vendored browser assets copied into the output site.
- `justfile` provides the normal commands for exporting, building, serving, and cleaning.

## Configuration

`site.yml` is the source of truth for the build architecture.

```yml
site:
  title: Advanced Cosmology
  output: public
  static: static

notes:
  root: notes
  public_prefix: ""

fragments:
  root: build

latex:
  root: build/latex
  header: site/latex/header.tex

templates:
  page: site/templates/page.html
  index: site/templates/index.html

assets:
  - from: site/static
    to: static
  - from: results
    to: results
  - from: notes/figures
    to: figures

index:
  title: Notes
  description: Course and project notes
```

Important fields:

- `site.title`: site name shown in templates.
- `site.output`: final generated website directory.
- `site.static`: URL path, relative to `site.output`, where template CSS and JS are served from.
- `notes.root`: Org source directory.
- `notes.public_prefix`: optional subdirectory for generated note pages inside `site.output`.
- `fragments.root`: directory where `export-fragments.el` writes body-only HTML fragments.
- `latex.root`: directory where `export-fragments.el` writes full LaTeX documents.
- `latex.header`: shared LaTeX preamble content injected into every exported document.
- `templates.page`: template for note pages.
- `templates.index`: template for the index page.
- `assets`: directories copied into the output site. The `site/static` mapping carries local fonts and MathJax under `static/vendor/`.
- `index.title` and `index.description`: metadata and visible title for `index.html`.

`site.static` should match the `to` path for the `site/static` asset mapping unless you also change the templates.

Changing `notes.root` or `fragments.root` changes both the exporter and the builder. Changing `site.output` changes the builder and the `serve`/`clean` commands.

## Org Notes

Each note should include at least:

```org
#+TITLE: A note title
#+DESCRIPTION: A short page description
```

The builder reads metadata from the Org source, not from the exported HTML.

Body-only Org export intentionally omits the Org title block. The page title comes from `#+TITLE` and is inserted by the template.

Local image links should point to assets that are copied by `site.yml`. For example:

```org
[[file:figures/sine_wave.png]]
```

works with:

```yml
assets:
  - from: notes/figures
    to: figures
```

for top-level notes.

## LaTeX Notes

A note can be written directly in LaTeX instead of Org. Put a `.tex` file under `notes/` and it is picked up automatically. `notes/example_latex.tex` is a worked example.

`export_tex.py` converts each `.tex` note with pandoc into the same kind of body-only fragment the Org exporter produces, so LaTeX notes get the same index card, sidebar navigation, theme, and link checking. Conversion:

- leaves math as raw TeX for MathJax (`\(...\)`, `\[...\]`, `align`, etc.);
- shifts headings down one level, so `\section` becomes `<h2>` like an Org note (the template `<h1>` is the page title);
- turns `\begin{info}...\end{info}` into `<div class="info">`, matching the Org special block. Other admonition names already styled by the theme (`warning`, `theorem`, `definition`, `proof`, `note`, `tip`) work the same way if you define the environment in LaTeX;
- highlights code blocks and aliases pandoc's classes onto the same palette as the Org notes.

### Metadata

The builder reads the same metadata from a `.tex` note using `%+` comment lines, which LaTeX ignores. They must come **before** `\documentclass`:

```latex
%+TITLE: A note title
%+DESCRIPTION: A short page description
\documentclass{article}
...
```

Only `TITLE` is required. A `.tex` and an `.org` note that would build to the same page (for example `foo.tex` and `foo.org`) is a hard error.

### Macros

Define reusable macros with plain `\newcommand` in `site/latex/macros.tex` and `\input` it from a note:

```latex
\input{../site/latex/macros}
```

pandoc expands `\newcommand` macros — including ones with arguments, and inside math — while converting, so **MathJax never sees them** and there is nothing to keep in sync. The same file is used natively when you compile the note to a PDF, so one definition serves both the web and print.

Exotic definitions (`\def`, `xparse`, macros with optional arguments) may not be expanded by pandoc. If you must use one inside math, either avoid it in `.tex` notes or also declare it in the MathJax `tex.macros` config in `site/templates/page.html`.

### PDFs

A `.tex` note is already LaTeX, so its PDF comes straight from `pdflatex` — no Org→LaTeX step. `\input` and `\includegraphics` paths resolve relative to the note's own directory, both for pandoc and for a PDF build, so compile from that directory:

```sh
cd notes && pdflatex example_latex.tex
```

`just latex` copies the `.tex` sources into `latex.root` (alongside the LaTeX that Org notes export), giving one directory with the LaTeX for every note.

### Limitations

- Info boxes on the web do not render a tcolorbox title; `\begin{info}[...]` options are dropped. Use a bold lead-in or a subsection instead.
- pandoc understands math, sectioning, and common constructs, not arbitrary package behavior. Keep `.tex` notes math- and prose-focused, as the Org notes are.
- Code syntax classes come from pandoc, not Org's htmlize, so a language must be given (for example `\begin{lstlisting}[language=Python]`) for highlighting.

Shared LaTeX includes (`macros.tex`, `header.tex`) live in `site/latex/`, not in `notes/`, so that every `.tex` file under `notes/` is a real note.

## Commands

List commands:

```sh
just
```

Export Org notes to HTML fragments:

```sh
just fragments
```

Export LaTeX notes to HTML fragments (pandoc):

```sh
just tex-fragments
```

Build the final site from existing fragments:

```sh
just build
```

Export both note types and build:

```sh
just quick
```

Export full LaTeX documents from Org notes and copy `.tex` note sources into `latex.root`:

```sh
just latex
```

Export, build, and serve locally, optionally on a custom port:

```sh
just site
just site 9000
```

Serve the already-built site, optionally on a custom port:

```sh
just serve
just serve 9000
```

The development server keeps running while you regenerate the site. Press `Ctrl+R` in the server terminal to run `just quick`; press `Ctrl+C` to stop serving. If you need the plain Python server without hotkeys, use:

```sh
just serve-static
```

Remove generated output:

```sh
just clean
```

`just serve` and `just clean` read their output directories from `site.yml`.

## Emacs Exporter

`export-fragments.el` uses Org's HTML exporter for body-only site fragments and the LaTeX exporter for full documents. LaTeX exports include transclusions and remove blank lines immediately surrounding display equations without modifying the Org sources. The exporter disables code execution during export:

```elisp
(setq org-export-use-babel nil)
```

The usual command uses a running Emacs server:

```sh
emacsclient --eval '(progn (load-file "/path/to/export-fragments.el") (my/site-export-all-fragments))'
```

The `just fragments` recipe runs this form for the current project. `just latex` calls `my/site-export-all-latex` and writes mirrored `.tex` files under `latex.root`.

If no Emacs server is available, use the batch fallback:

```sh
emacs --batch --no-site-file -l export-fragments.el \
  --eval '(my/site-export-all-fragments)'
```

The exporter tries to load `htmlize` from the current Emacs environment. In batch mode, it also looks under the configured Doom Emacs package build directory.

## Python Builder

`build_site.py` requires Python and PyYAML.

Run it directly with:

```sh
python build_site.py
```

It performs these steps:

1. Reads `site.yml`.
2. Finds Org (`.org`) and LaTeX (`.tex`) notes under `notes.root`, and errors if two of them would build to the same page.
3. Reads `TITLE` and optional `DESCRIPTION` metadata from each source (`#+` in Org, `%+` in LaTeX). Metadata keys are case-insensitive.
4. Reads the matching HTML fragment from `fragments.root`.
5. Renders note pages and `index.html`.
6. Copies configured assets.
7. Validates local `href` and `src` links in generated HTML.

Note pages also add the current note section headings to the sidebar navigation by reading heading IDs from the exported fragment. The builder still leaves the Org-generated body HTML unchanged.

Fonts and MathJax are vendored under `site/static/vendor/`, so generated pages do not depend on Google Fonts, jsdelivr, or any other network resource at load time.

The builder deliberately does not parse or rewrite Org-generated body HTML.
