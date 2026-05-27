#!/usr/bin/env python3
from __future__ import annotations

import html
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "site.yml"

META_RE = re.compile(r"^#\+([A-Z0-9_]+):\s*(.*?)\s*$")
LINK_RE = re.compile(r"""(?:href|src)=["']([^"'#]+(?:#[^"']*)?)["']""")
PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-z_][a-z0-9_]*)\s*\}\}")

REQUIRED_META = ("TITLE", "DESCRIPTION")


@dataclass(frozen=True)
class AssetMapping:
    source: Path
    target: Path


@dataclass(frozen=True)
class SiteConfig:
    site_title: str
    notes_dir: Path
    fragments_dir: Path
    public_dir: Path
    static_public_path: Path
    notes_public_prefix: Path
    page_template: Path
    index_template: Path
    assets: tuple[AssetMapping, ...]
    index_title: str
    index_description: str


@dataclass(frozen=True)
class NoteMeta:
    source_path: Path
    relative_path: Path
    slug: str
    title: str
    description: str

    @property
    def html_path(self) -> Path:
        return self.relative_path.with_suffix(".html")


def path_from_config(value: object, key: str) -> Path:
    if not isinstance(value, str) or not value:
        fail(f"site.yml field {key} must be a non-empty path string")
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def public_relative_path(value: object, key: str) -> Path:
    if value is None:
        fail(f"site.yml field {key} must be a path string")
    if not isinstance(value, str):
        fail(f"site.yml field {key} must be a path string")
    if value.startswith("/"):
        fail(f"site.yml field {key} must be relative, not absolute")
    return Path(value) if value else Path()


def string_from_config(value: object, key: str) -> str:
    if not isinstance(value, str) or not value:
        fail(f"site.yml field {key} must be a non-empty string")
    return value


def section(config: dict[str, object], key: str) -> dict[str, object]:
    value = config.get(key)
    if not isinstance(value, dict):
        fail(f"site.yml section {key} is missing or invalid")
    return value


def load_config(path: Path = CONFIG_PATH) -> SiteConfig:
    ensure_exists(path, "site configuration")
    raw = yaml.safe_load(read_text(path))
    if not isinstance(raw, dict):
        fail(f"{path} must contain a YAML mapping")

    site = section(raw, "site")
    notes = section(raw, "notes")
    fragments = section(raw, "fragments")
    templates = section(raw, "templates")
    index = section(raw, "index")

    public_dir = path_from_config(site.get("output"), "site.output")

    assets_raw = raw.get("assets", [])
    if not isinstance(assets_raw, list):
        fail("site.yml field assets must be a list")

    assets: list[AssetMapping] = []
    for i, asset in enumerate(assets_raw, start=1):
        if not isinstance(asset, dict):
            fail(f"site.yml assets item {i} must be a mapping")
        source = path_from_config(asset.get("from"), f"assets[{i}].from")
        target = public_dir / public_relative_path(asset.get("to"), f"assets[{i}].to")
        assets.append(AssetMapping(source=source, target=target))

    return SiteConfig(
        site_title=string_from_config(site.get("title"), "site.title"),
        notes_dir=path_from_config(notes.get("root"), "notes.root"),
        fragments_dir=path_from_config(fragments.get("root"), "fragments.root"),
        public_dir=public_dir,
        static_public_path=public_relative_path(site.get("static", "static"), "site.static"),
        notes_public_prefix=public_relative_path(
            notes.get("public_prefix", ""), "notes.public_prefix"
        ),
        page_template=path_from_config(templates.get("page"), "templates.page"),
        index_template=path_from_config(templates.get("index"), "templates.index"),
        assets=tuple(assets),
        index_title=string_from_config(index.get("title"), "index.title"),
        index_description=string_from_config(
            index.get("description"), "index.description"
        ),
    )


def fail(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")


def ensure_exists(path: Path, what: str) -> None:
    if not path.exists():
        fail(f"missing {what}: {path}")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def copy_tree_if_exists(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def parse_org_metadata(path: Path) -> dict[str, str]:
    """
    Read metadata from the initial header block of an Org file.

    We keep this deliberately simple: scan from the top, allow blank lines,
    stop once real content begins.
    """
    meta: dict[str, str] = {}

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()

            if not stripped:
                continue

            if stripped.startswith("#+"):
                m = META_RE.match(line)
                if m:
                    key, value = m.groups()
                    meta[key] = value.strip()
                continue

            # First real content line: stop scanning metadata.
            break

    return meta


def load_note_meta(path: Path, notes_dir: Path) -> NoteMeta:
    meta = parse_org_metadata(path)

    missing = [key for key in REQUIRED_META if not meta.get(key)]
    if missing:
        fail(f"{path} is missing required metadata: {', '.join(missing)}")

    relative_path = path.relative_to(notes_dir)

    return NoteMeta(
        source_path=path,
        relative_path=relative_path,
        slug=relative_path.with_suffix("").as_posix(),
        title=meta["TITLE"],
        description=meta["DESCRIPTION"],
    )


def render_template(template: str, context: dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in context:
            fail(f"template placeholder {{{{{key}}}}} has no value")
        return context[key]

    return PLACEHOLDER_RE.sub(repl, template)


def relative_href(from_file: Path, to_file: Path) -> str:
    return os.path.relpath(to_file, start=from_file.parent).replace(os.sep, "/")


def note_public_path(config: SiteConfig, note: NoteMeta) -> Path:
    return config.public_dir / config.notes_public_prefix / note.html_path


def note_card(config: SiteConfig, note: NoteMeta) -> str:
    title = html.escape(note.title)
    description = html.escape(note.description)
    href = html.escape(
        relative_href(config.public_dir / "index.html", note_public_path(config, note))
    )

    return f"""<article class="note-card">
  <h2><a href="{href}">{title}</a></h2>
  <p class="note-description">{description}</p>
</article>"""


def build_nav(
    config: SiteConfig,
    notes: list[NoteMeta],
    current_file: Path,
    current_slug: str | None = None,
) -> str:
    items: list[str] = []

    for note in notes:
        active = ' class="active"' if note.slug == current_slug else ""
        href = html.escape(relative_href(current_file, note_public_path(config, note)))
        title = html.escape(note.title)
        items.append(f'    <li{active}><a href="{href}">{title}</a></li>')

    return '<nav class="notes-nav">\n  <ol>\n' + "\n".join(items) + "\n  </ol>\n</nav>"


def build_single_note(
    config: SiteConfig,
    note: NoteMeta,
    notes: list[NoteMeta],
    page_template: str,
) -> None:
    fragment_path = config.fragments_dir / note.html_path
    ensure_exists(fragment_path, f"HTML fragment for {note.slug}")

    body = read_text(fragment_path)
    output_path = note_public_path(config, note)

    page_html = render_template(
        page_template,
        {
            "title": html.escape(note.title),
            "description": html.escape(note.description),
            "site_title": html.escape(config.site_title),
            "static": html.escape(
                relative_href(output_path, config.public_dir / config.static_public_path)
            ),
            "home": html.escape(relative_href(output_path, config.public_dir / "index.html")),
            "nav": build_nav(config, notes, output_path, current_slug=note.slug),
            "body": body,
        },
    )

    write_text(output_path, page_html)


def build_index(config: SiteConfig, notes: list[NoteMeta], index_template: str) -> None:
    content = "\n\n".join(note_card(config, note) for note in notes)
    output_path = config.public_dir / "index.html"

    index_html = render_template(
        index_template,
        {
            "title": html.escape(config.index_title),
            "description": html.escape(config.index_description),
            "site_title": html.escape(config.site_title),
            "static": html.escape(
                relative_href(output_path, config.public_dir / config.static_public_path)
            ),
            "home": html.escape(relative_href(output_path, config.public_dir / "index.html")),
            "nav": build_nav(config, notes, output_path, current_slug=None),
            "content": content,
        },
    )

    write_text(output_path, index_html)
    write_text(
        config.public_dir / "_nav.html",
        build_nav(config, notes, output_path, current_slug=None),
    )


def local_link_targets(html_path: Path) -> list[Path]:
    """
    Extract local href/src targets from one HTML file and resolve them
    relative to that file.
    """
    text = read_text(html_path)
    targets: list[Path] = []

    for raw in LINK_RE.findall(text):
        # Remove any fragment/query part.
        split = urlsplit(raw)
        link = split.path

        if not link:
            continue

        # Skip external/protocol links.
        if raw.startswith(
            ("http://", "https://", "mailto:", "tel:", "javascript:", "//")
        ):
            continue

        # Resolve relative to the HTML file.
        resolved = (html_path.parent / link).resolve()
        targets.append(resolved)

    return targets


def validate_links(config: SiteConfig) -> None:
    """
    Check that local href/src links inside generated HTML point to existing files.
    This catches broken note links and figure links immediately.
    """
    public_root = config.public_dir.resolve()
    broken: list[str] = []

    for html_file in config.public_dir.rglob("*.html"):
        for target in local_link_targets(html_file):
            try:
                target.relative_to(public_root)
            except ValueError:
                broken.append(f"{html_file.name} -> escapes public/: {target}")
                continue

            if not target.exists():
                broken.append(
                    f"{html_file.name} -> missing target: {target.relative_to(public_root)}"
                )

    if broken:
        msg = "\n".join(f"  - {line}" for line in broken)
        fail("broken local links found:\n" + msg)


def main() -> None:
    config = load_config()

    ensure_exists(config.notes_dir, "notes directory")
    ensure_exists(config.page_template, "page template")
    ensure_exists(config.index_template, "index template")

    clean_dir(config.public_dir)

    notes = sorted(
        (load_note_meta(path, config.notes_dir) for path in config.notes_dir.rglob("*.org")),
        key=lambda n: n.slug,
    )

    if not notes:
        fail(f"no .org notes found in {config.notes_dir}")

    page_template = read_text(config.page_template)
    index_template = read_text(config.index_template)

    for note in notes:
        build_single_note(config, note, notes, page_template)

    build_index(config, notes, index_template)

    for asset in config.assets:
        copy_tree_if_exists(asset.source, asset.target)

    validate_links(config)

    print(f"Built {len(notes)} notes into {config.public_dir}")


if __name__ == "__main__":
    main()
