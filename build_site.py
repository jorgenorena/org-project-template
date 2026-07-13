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

META_RE = re.compile(r"^[#%]\+([A-Z0-9_]+):\s*(.*?)\s*$", re.IGNORECASE)
LINK_RE = re.compile(r"""(?:href|src)=["']([^"'#]+(?:#[^"']*)?)["']""")
PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-z_][a-z0-9_]*)\s*\}\}")
HEADING_RE = re.compile(
    r"""<h([2-4])\b[^>]*\bid=["']([^"']+)["'][^>]*>(.*?)</h\1>""",
    re.IGNORECASE | re.DOTALL,
)
TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")

REQUIRED_META = ("TITLE",)


@dataclass(frozen=True)
class AssetMapping:
    source: Path
    target: Path


@dataclass(frozen=True)
class SectionConfig:
    """A notes/ subfolder rendered as its own submenu in the site nav.

    Only subfolders listed here are scanned for notes; every other subfolder
    (figures/, other asset dirs) is left alone. ``name`` is the path relative
    to ``notes.root``; ``title`` is the submenu heading.
    """

    name: str
    title: str


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
    sections: tuple[SectionConfig, ...]
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


@dataclass(frozen=True)
class NoteSection:
    level: int
    anchor: str
    title: str


@dataclass(frozen=True)
class NoteGroup:
    """A run of notes in the nav. ``title`` is ``None`` for top-level notes
    (rendered ungrouped) and the section title for a subfolder submenu."""

    title: str | None
    notes: tuple[NoteMeta, ...]


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

    sections = parse_sections(notes.get("sections", []))

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
        sections=sections,
        index_title=string_from_config(index.get("title"), "index.title"),
        index_description=string_from_config(
            index.get("description"), "index.description"
        ),
    )


def parse_sections(value: object) -> tuple[SectionConfig, ...]:
    """Parse ``notes.sections`` into ordered SectionConfig entries.

    Each entry is either a bare subfolder name (``"algebra"``) or a mapping
    with an explicit title (``{dir: algebra, title: Algebra}``). The title
    defaults to the folder name when omitted.
    """
    if value is None:
        return ()
    if not isinstance(value, list):
        fail("site.yml field notes.sections must be a list")

    sections: list[SectionConfig] = []
    for i, item in enumerate(value, start=1):
        if isinstance(item, str):
            name, title = item, item
        elif isinstance(item, dict):
            raw_name = item.get("dir")
            if not isinstance(raw_name, str) or not raw_name:
                fail(f"site.yml notes.sections[{i}].dir must be a non-empty string")
            name = raw_name
            raw_title = item.get("title", name)
            if not isinstance(raw_title, str) or not raw_title:
                fail(f"site.yml notes.sections[{i}].title must be a non-empty string")
            title = raw_title
        else:
            fail(f"site.yml notes.sections[{i}] must be a string or a mapping")

        parts = Path(name).parts
        if name.startswith("/") or ".." in parts:
            fail(f"site.yml notes.sections[{i}].dir must be a relative path inside notes/")
        sections.append(SectionConfig(name=Path(name).as_posix(), title=title))

    return tuple(sections)


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


def parse_note_metadata(path: Path) -> dict[str, str]:
    """
    Read metadata from the initial header block of a note.

    Works for both Org (``#+KEY: value``) and LaTeX (``%+KEY: value``)
    sources. We keep this deliberately simple: scan from the top, allow
    blank lines, stop once real content begins. For LaTeX notes this means
    the ``%+`` metadata comments must come before ``\\documentclass``.
    """
    meta: dict[str, str] = {}

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            m = META_RE.match(line)
            if m:
                key, value = m.groups()
                meta[key.upper()] = value.strip()
                continue

            # First real content line: stop scanning metadata.
            break

    return meta


def load_note_meta(path: Path, notes_dir: Path) -> NoteMeta:
    meta = parse_note_metadata(path)

    missing = [key for key in REQUIRED_META if not meta.get(key)]
    if missing:
        fail(f"{path} is missing required metadata: {', '.join(missing)}")

    relative_path = path.relative_to(notes_dir)

    return NoteMeta(
        source_path=path,
        relative_path=relative_path,
        slug=relative_path.with_suffix("").as_posix(),
        title=meta["TITLE"],
        description=meta.get("DESCRIPTION", ""),
    )


def find_notes(directory: Path, notes_dir: Path, recursive: bool) -> list[NoteMeta]:
    globber = directory.rglob if recursive else directory.glob
    paths = [*globber("*.org"), *globber("*.tex")]
    notes = [load_note_meta(path, notes_dir) for path in paths]
    notes.sort(key=lambda n: n.slug)
    return notes


def discover_note_groups(config: SiteConfig) -> list[NoteGroup]:
    """Discover notes as ordered nav groups.

    Top-level notes (directly in ``notes.root``) come first, ungrouped. Then
    one group per configured section, scanned recursively within that
    subfolder. Subfolders that are not listed as sections are never scanned,
    so asset folders (figures, etc.) are ignored rather than rendered.
    """
    groups = [NoteGroup(title=None, notes=tuple(find_notes(config.notes_dir, config.notes_dir, recursive=False)))]

    for section in config.sections:
        section_dir = config.notes_dir / section.name
        ensure_exists(section_dir, f"notes section directory '{section.name}'")
        if not section_dir.is_dir():
            fail(f"notes section '{section.name}' is not a directory: {section_dir}")
        notes = find_notes(section_dir, config.notes_dir, recursive=True)
        groups.append(NoteGroup(title=section.title, notes=tuple(notes)))

    return groups


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


def clean_heading_text(value: str) -> str:
    text = TAG_RE.sub("", value)
    text = html.unescape(text)
    return WHITESPACE_RE.sub(" ", text).strip()


def extract_note_sections(body: str) -> list[NoteSection]:
    sections: list[NoteSection] = []

    for match in HEADING_RE.finditer(body):
        level = int(match.group(1))
        anchor = html.unescape(match.group(2))
        title = clean_heading_text(match.group(3))

        if title:
            sections.append(NoteSection(level=level, anchor=anchor, title=title))

    return sections


def build_section_nav(sections: list[NoteSection]) -> str:
    if not sections:
        return ""

    items: list[str] = []
    for section in sections:
        title = html.escape(section.title)
        anchor = html.escape(section.anchor, quote=True)
        items.append(
            f'      <li class="section-level-{section.level}">'
            f'<a href="#{anchor}">{title}</a></li>'
        )

    return '\n      <ol class="note-sections">\n' + "\n".join(items) + "\n      </ol>\n    "


def build_nav_list(
    config: SiteConfig,
    notes: tuple[NoteMeta, ...],
    current_file: Path,
    current_slug: str | None,
    current_sections: list[NoteSection],
    indent: str,
) -> str:
    items: list[str] = []
    for note in notes:
        active = ' class="active"' if note.slug == current_slug else ""
        href = html.escape(relative_href(current_file, note_public_path(config, note)))
        title = html.escape(note.title)
        sections = build_section_nav(current_sections) if note.slug == current_slug else ""
        items.append(f'{indent}  <li{active}><a href="{href}">{title}</a>{sections}</li>')

    return f'{indent}<ol class="nav-list">\n' + "\n".join(items) + f"\n{indent}</ol>"


def build_nav(
    config: SiteConfig,
    groups: list[NoteGroup],
    current_file: Path,
    current_slug: str | None = None,
    current_sections: list[NoteSection] | None = None,
) -> str:
    current_sections = current_sections or []
    blocks: list[str] = []

    for group in groups:
        if not group.notes:
            continue

        if group.title is None:
            blocks.append(
                build_nav_list(
                    config, group.notes, current_file, current_slug, current_sections, "  "
                )
            )
        else:
            title = html.escape(group.title)
            nav_list = build_nav_list(
                config, group.notes, current_file, current_slug, current_sections, "    "
            )
            blocks.append(
                f'  <div class="nav-group">\n'
                f'    <h2 class="nav-group-title">{title}</h2>\n'
                f"{nav_list}\n"
                f"  </div>"
            )

    return '<nav class="notes-nav">\n' + "\n".join(blocks) + "\n</nav>"


def build_single_note(
    config: SiteConfig,
    note: NoteMeta,
    groups: list[NoteGroup],
    page_template: str,
) -> None:
    fragment_path = config.fragments_dir / note.html_path
    ensure_exists(fragment_path, f"HTML fragment for {note.slug}")

    body = read_text(fragment_path)
    sections = extract_note_sections(body)
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
            "nav": build_nav(
                config,
                groups,
                output_path,
                current_slug=note.slug,
                current_sections=sections,
            ),
            "body": body,
        },
    )

    write_text(output_path, page_html)


def check_slug_clashes(notes: list[NoteMeta]) -> None:
    """
    Fail if two source notes build to the same output slug.

    An ``.org`` and a ``.tex`` note with the same name (e.g. ``foo.org`` and
    ``foo.tex``) would both target ``foo.html`` and collide in the nav.
    """
    seen: dict[str, Path] = {}

    for note in notes:
        existing = seen.get(note.slug)
        if existing is not None:
            fail(
                f"note slug clash: {existing} and {note.source_path} both build "
                f"to '{note.slug}.html'. Rename one of them."
            )
        seen[note.slug] = note.source_path


def build_index(config: SiteConfig, groups: list[NoteGroup], index_template: str) -> None:
    output_path = config.public_dir / "index.html"

    card_blocks: list[str] = []
    for group in groups:
        if not group.notes:
            continue
        if group.title is not None:
            card_blocks.append(f'<h2 class="note-group-title">{html.escape(group.title)}</h2>')
        card_blocks.extend(note_card(config, note) for note in group.notes)
    content = "\n\n".join(card_blocks)

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
            "nav": build_nav(config, groups, output_path, current_slug=None),
            "content": content,
        },
    )

    write_text(output_path, index_html)
    write_text(
        config.public_dir / "_nav.html",
        build_nav(config, groups, output_path, current_slug=None),
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
            (
                "http://",
                "https://",
                "mailto:",
                "tel:",
                "data:",
                "javascript:",
                "//",
            )
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

    groups = discover_note_groups(config)
    notes = [note for group in groups for note in group.notes]

    if not notes:
        fail(f"no .org or .tex notes found in {config.notes_dir}")

    check_slug_clashes(notes)

    page_template = read_text(config.page_template)
    index_template = read_text(config.index_template)

    for note in notes:
        build_single_note(config, note, groups, page_template)

    build_index(config, groups, index_template)

    for asset in config.assets:
        copy_tree_if_exists(asset.source, asset.target)

    validate_links(config)

    print(f"Built {len(notes)} notes into {config.public_dir}")


if __name__ == "__main__":
    main()
