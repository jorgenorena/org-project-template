# Advanced Cosmology Notes Site

This project builds a static website from Org-mode notes.

The build has two stages:

1. `export-fragments.el` exports each `.org` note to a body-only HTML fragment.
2. `build_site.py` wraps those fragments with HTML templates, builds the index and navigation, copies assets, and validates local links.

The intended data flow is:

```text
notes/foo.org
  -> build/foo.html
  -> public/foo.html
```

Nested notes keep the same relative path:

```text
notes/project/bar.org
  -> build/project/bar.html
  -> public/project/bar.html
```

## Files

- `site.yml` defines the site architecture: source paths, fragment paths, output paths, templates, copied assets, and index metadata.
- `export-fragments.el` is the Emacs/Org exporter. It reads `notes.root` and `fragments.root` from `site.yml`.
- `build_site.py` is the static-site builder. It reads `site.yml`, loads note metadata from Org headers, wraps fragments with templates, copies assets, and checks links.
- `site/templates/` contains plain HTML templates with `{{ placeholder }}` replacement.
- `site/static/` contains CSS and JavaScript copied into the output site.
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
- `templates.page`: template for note pages.
- `templates.index`: template for the index page.
- `assets`: directories copied into the output site.
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

## Commands

List commands:

```sh
just
```

Export Org notes to HTML fragments:

```sh
just fragments
```

Build the final site from existing fragments:

```sh
just build
```

Export and build:

```sh
just quick
```

Export, build, and serve locally:

```sh
just site
```

Serve the already-built site:

```sh
just serve
```

Remove generated output:

```sh
just clean
```

`just serve` and `just clean` read the output and fragment directories from `site.yml`.

## Emacs Exporter

`export-fragments.el` uses Org's HTML exporter with body-only output. It disables code execution during export:

```elisp
(setq org-export-use-babel nil)
```

The usual command uses a running Emacs server:

```sh
emacsclient --eval '(progn (load-file "/path/to/export-fragments.el") (my/site-export-all-fragments))'
```

The `just fragments` recipe runs this form for the current project.

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
2. Finds Org notes under `notes.root`.
3. Reads `#+TITLE` and `#+DESCRIPTION`.
4. Reads the matching HTML fragment from `fragments.root`.
5. Renders note pages and `index.html`.
6. Copies configured assets.
7. Validates local `href` and `src` links in generated HTML.

The builder deliberately does not parse or rewrite Org-generated body HTML.
