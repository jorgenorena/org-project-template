# Codex Project Context: Org Notes Static Site

This project turns Org-mode scientific notes into a static website. Keep the system simple: Org/Emacs exports content fragments; Python wraps them into pages; CSS/JS handles presentation. Do not turn this into a web framework.

## Core idea

The project is shaped like a research/teaching project, not like a frontend/backend app.

- `notes/` contains Org notes.
- `code/` may contain Mathematica, Python, shell scripts, etc.
- `data/` may contain inputs.
- `results/` contains generated outputs: figures, tables, Mathematica snippets, logs.
- `references/` contains `.bib`, CSL files, papers.
- `site/` contains presentation machinery: templates, CSS, JS.
- `build/` contains intermediate exported HTML fragments.
- `public/` contains the disposable final website.

The website is a view of the project, not the project.

## Build pipeline

There are two stages.

1. Emacs exports Org notes to body-only HTML fragments.
2. `build_site.py` reads metadata, wraps fragments in templates, builds index/navigation, copies assets, and validates links.

The Python builder must not parse or rewrite Org-generated body HTML. It should preserve equations, code blocks, special blocks, citations, figure links, and inter-note links.

## Configuration and path contract

`site.yml` is the source of truth for site architecture. The Python builder
reads the full file. The Emacs exporter reads `notes.root` and
`fragments.root`.

Keep the default paths simple and mirrored.

```text
notes/foo.org
  -> build/foo.html
  -> public/foo.html

notes/project/bar.org
  -> build/project/bar.html
  -> public/project/bar.html
```

Default project paths:

- Org sources: `notes/`
- HTML fragments: `build/`
- Templates: `site/templates/`
- Static CSS/JS: `site/static/`, copied to `public/static/`
- Note figures: `notes/figures/`, copied to `public/figures/`
- Final site: `public/`

Reference `site.yml`:

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

## Note metadata

Each Org file should start with simple metadata.

```org
#+TITLE: FLRW background cosmology
#+DATE: 2026-04-24
#+DESCRIPTION: Expansion, horizons, and distances
#+SECTION: Lectures
#+ORDER: 02
#+BIBLIOGRAPHY: ../references/references.bib
#+CITE_EXPORT: csl ../references/csl/style.csl
```

Required:

- `TITLE`
- `DESCRIPTION`

Optional but useful:

- `DATE`
- `SECTION`
- `ORDER`

The builder reads metadata from the Org source, not from the exported HTML.

## Template contract

Templates are plain HTML files with simple `{{ placeholder }}` replacement. No Jinja, no React, no framework.

Required placeholders for `page.html`:

```html
<title>{{ title }}</title>
<meta name="description" content="{{ description }}" />

<link rel="stylesheet" href="{{ static }}/themes.css" />
<link rel="stylesheet" href="{{ static }}/base.css" />
<script defer src="{{ static }}/theme.js"></script>
<script defer src="{{ static }}/menu.js"></script>

<a class="site-title" href="{{ home }}">{{ site_title }}</a>

<aside id="site-sidebar" class="sidebar">{{ nav }}</aside>

<main class="page">
  <header class="page-header">
    <h1>{{ title }}</h1>
  </header>
  {{ body }}
</main>
```

Required placeholders for `index.html`:

```html
<title>{{ title }}</title>
<meta name="description" content="{{ description }}" />

<link rel="stylesheet" href="{{ static }}/themes.css" />
<link rel="stylesheet" href="{{ static }}/base.css" />
<script defer src="{{ static }}/theme.js"></script>
<script defer src="{{ static }}/menu.js"></script>

<a class="site-title" href="{{ home }}">{{ site_title }}</a>

<aside id="site-sidebar" class="sidebar">{{ nav }}</aside>

<main class="page">
  <header class="page-header">
    <h1>{{ title }}</h1>
  </header>
  {{ content }}
</main>
```

Load `themes.css` before `base.css`.

## CSS/JS conventions

CSS is split into:

- `site/static/themes.css`: variables only, including dark theme and Solarized Light.
- `site/static/base.css`: layout, typography, Org HTML styling, nav, code blocks, info boxes.

Current visual goals:

- Dark theme resembling Doom Peacock but darker.
- Solarized Light as light theme.
- Prose font: IBM Plex Serif.
- Code font: Fira Code.
- Fira Code should be used only for code-like elements.
- Headers are white in dark mode.
- Links are dark red and underlined.
- `=code=` should be green.
- `~verbatim~` should be dark red.
- Nav menu is a numbered list, not boxed.
- Active nav item has only a vertical green bar left of the number.
- Avoid rounded boxes unless truly useful.

JS is tiny:

- `theme.js` toggles `html[data-theme="dark"|"light"]` and stores preference in local storage.
- `menu.js` toggles the mobile sidebar with `body.menu-open`.

Do not introduce a frontend framework.

## Org export behavior

Org body-only export intentionally omits the document title block. Therefore:

- `#+TITLE` is used by the builder for `<title>` and visible page `<h1>`.
- The exported Org body starts with actual note sections, usually as `<h2>`.

Org source blocks should be exported with semantic htmlize spans. The exported fragment should contain classes such as:

```html
<span class="org-keyword">import</span>
<span class="org-variable-name">x</span>
<span class="org-string">'file.png'</span>
```

If colors do not appear, first check that `themes.css` defines syntax variables used by `base.css`, e.g. `--syntax-keyword`, `--syntax-string`, `--syntax-variable`.

## Bibliography

Use Org native citations and a BibTeX file.

For website export, use CSL:

```org
#+BIBLIOGRAPHY: ../references/references.bib
#+CITE_EXPORT: csl ../references/csl/style.csl
```

Place bibliography with:

```org
#+PRINT_BIBLIOGRAPHY:
```

The builder should not format citations or bibliography.

## Figures and generated outputs

Generated plots and Mathematica outputs should usually live in `results/`.

Examples:

```text
results/figures/charge_scaling.pdf
results/mathematica/leading_charge.tex
```

The builder copies asset mappings from `site.yml`, such as
`site/static/ -> public/static/`, `results/ -> public/results/`, and
`notes/figures/ -> public/figures/`.

Notes should link to generated files with normal Org file links. Preserve directory structure where possible so relative links remain meaningful.

## Link validation

The builder should validate local `href` and `src` links in generated HTML.

It should catch broken links to:

- notes
- figures
- generated results
- CSS/JS/static assets

It should skip external links like `https://`, `mailto:`, `tel:`, `data:`, and `#anchors`.

If validation becomes annoying, fix the link or asset mapping. Do not silently disable validation.

## Automation

Preferred workflow is command-runner style, not a long README.

Typical commands should eventually be exposed by a `justfile`:

```make
default:
    just --list

fragments:
    emacsclient --eval '(progn (load-file "{{justfile_directory()}}/export-fragments.el") (my/site-export-all-fragments))'

build:
    python build_site.py

serve:
    python -m http.server 8000 --directory public

quick: fragments build

site: fragments build serve

clean:
    rm -rf build public
```

The human-facing documentation should be roughly:

> Edit Org notes in `notes/` and generate outputs into `results/`.
> Run `just site` to render and serve the website; run `just quick` to rebuild without serving.

## Design constraints

Prefer dumb, explicit, debuggable code.

Avoid:

- React
- Django
- heavy static-site generators
- complex templating
- automatic code execution during note rendering
- parsing/restructuring Org-generated body HTML
- excessive config magic
- long READMEs

Accept:

- one small YAML config
- one Python builder
- one Emacs export script
- one `justfile`
- plain HTML templates
- plain CSS/JS

The goal is to make notes render quickly on desktop, cluster, or Termux/mobile workflows without slowing down rendering by executing code. Code execution happens separately and writes reproducible outputs into `results/`.
