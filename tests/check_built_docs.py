#!/usr/bin/env python3
"""Validate the rendered MkDocs site and approval-bound deployment contract."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import yaml


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_LOCATIONS = {
    "index.html",
    "start/installation/index.html",
    "start/first-fix/index.html",
    "concepts/skills-loops-kernel/index.html",
    "guides/build/index.html",
    "guides/fix/index.html",
    "guides/review/index.html",
    "guides/resume/index.html",
    "guides/provider-setup/index.html",
    "reference/public-commands/index.html",
    "reference/advanced-kernel/index.html",
    "reference/configuration/index.html",
    "reference/artifacts-and-schemas/index.html",
    "reference/stop-reasons/index.html",
    "trust/support-matrix/index.html",
    "trust/security-privacy/index.html",
    "trust/benchmark/index.html",
    "trust/compatibility-deprecation/index.html",
    "contribute/development/index.html",
    "contribute/authoring/index.html",
    "contribute/behavioral-scenarios/index.html",
    "contribute/release-process/index.html",
    "release/docs-deployment/index.html",
    "release/RELEASING/index.html",
    "release/v0.9.0/index.html",
}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.html_lang = ""
        self.viewport = False
        self.main = False
        self.nav = False
        self.search = False
        self.canonical = ""
        self.hrefs: list[str] = []
        self.images_without_alt: list[str] = []
        self.text: list[str] = []

    def handle_data(self, data: str) -> None:
        self.text.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "html":
            self.html_lang = values.get("lang") or ""
        elif tag == "meta" and values.get("name") == "viewport":
            self.viewport = "width=device-width" in (values.get("content") or "")
        elif tag == "main":
            self.main = True
        elif tag == "nav":
            self.nav = True
        elif tag == "input" and values.get("type") == "text" and values.get("aria-label"):
            self.search = True
        elif tag == "link" and values.get("rel") == "canonical":
            self.canonical = values.get("href") or ""
        elif tag == "a" and values.get("href"):
            self.hrefs.append(values["href"] or "")
        elif tag == "img" and not (values.get("alt") or "").strip():
            self.images_without_alt.append(values.get("src") or "unknown")


def local_target(site: Path, page: Path, href: str) -> Path | None:
    parsed = urlparse(href)
    if parsed.scheme or href.startswith(("mailto:", "#")):
        return None
    raw = parsed.path
    if not raw:
        return None
    target = site / raw.lstrip("/") if raw.startswith("/") else page.parent / raw
    if raw.endswith("/") or target.is_dir():
        target = target / "index.html"
    return target.resolve()


def main() -> int:
    site = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "site"
    failures: list[str] = []
    config = yaml.safe_load((ROOT / "mkdocs.yml").read_text(encoding="utf-8"))
    base_url = config["site_url"].rstrip("/")
    docs_version = str(config["extra"]["adlc_version"])
    release_tag = f"v{docs_version}"

    for relative in sorted(REQUIRED_LOCATIONS):
        page = site / relative
        if not page.is_file():
            failures.append(f"missing rendered page: {relative}")
            continue
        parser = PageParser()
        text = page.read_text(encoding="utf-8")
        parser.feed(text)
        if parser.html_lang != "en":
            failures.append(f"{relative}: html lang is not en")
        if not parser.viewport:
            failures.append(f"{relative}: mobile viewport missing")
        if not parser.main or not parser.nav:
            failures.append(f"{relative}: main or nav landmark missing")
        if not parser.search:
            failures.append(f"{relative}: accessible search input missing")
        canonical_suffix = "" if relative == "index.html" else relative[: -len("index.html")]
        expected_canonical = f"{base_url}/{canonical_suffix}"
        if parser.canonical != expected_canonical:
            failures.append(f"{relative}: canonical URL is {parser.canonical}, expected {expected_canonical}")
        if parser.images_without_alt:
            failures.append(f"{relative}: image alt text missing")
        for href in parser.hrefs:
            parsed = urlparse(href)
            if parsed.scheme == "http":
                failures.append(f"{relative}: insecure external link {href}")
            target = local_target(site, page, href)
            if target is not None and site not in target.parents and target != site:
                failures.append(f"{relative}: local link escapes site {href}")
            elif target is not None and not target.exists():
                failures.append(f"{relative}: broken rendered link {href}")

    index_parser = PageParser()
    index = (site / "index.html").read_text(encoding="utf-8") if (site / "index.html").is_file() else ""
    index_parser.feed(index)
    if f"ADLC docs {docs_version}" not in index:
        failures.append("version announcement missing from rendered home")
    required_home_links = {
        "release": "https://github.com/bigeasyfreeman/adlc/releases",
        "repository social": "https://github.com/bigeasyfreeman/adlc",
        "edit": f"https://github.com/bigeasyfreeman/adlc/edit/{release_tag}/docs/index.md",
    }
    for label, href in required_home_links.items():
        if href not in index_parser.hrefs:
            failures.append(f"{label} link missing from rendered home")
    install_parser = PageParser()
    install_parser.feed((site / "start/installation/index.html").read_text(encoding="utf-8"))
    if "adlc-skill install" not in " ".join(" ".join(install_parser.text).split()):
        failures.append("installation snippet missing from rendered site")

    search_path = site / "search/search_index.json"
    if not search_path.is_file():
        failures.append("search index missing")
    else:
        search = json.loads(search_path.read_text(encoding="utf-8"))
        locations = {item.get("location", "").split("#", 1)[0] for item in search.get("docs", [])}
        for expected in ("start/first-fix/", "reference/public-commands/", "trust/support-matrix/"):
            if expected not in locations:
                failures.append(f"search index missing {expected}")

    for required in ("404.html", "sitemap.xml", "search/search_index.json"):
        if not (site / required).is_file():
            failures.append(f"missing site artifact: {required}")

    styles = "\n".join(path.read_text(encoding="utf-8") for path in site.glob("assets/stylesheets/*.css"))
    if "@media screen and (max-width" not in styles or "@media screen and (min-width" not in styles:
        failures.append("responsive stylesheet breakpoints missing")

    published_sources: list[Path] = []

    def collect_nav(value: object) -> None:
        if isinstance(value, str) and value.endswith(".md"):
            published_sources.append(ROOT / "docs" / value)
        elif isinstance(value, list):
            for child in value:
                collect_nav(child)
        elif isinstance(value, dict):
            for child in value.values():
                collect_nav(child)

    collect_nav(config["nav"])
    if config.get("edit_uri") != f"edit/{release_tag}/docs/":
        failures.append(f"edit_uri does not target release tag {release_tag}")
    mutable_source = re.compile(r"https://github\.com/bigeasyfreeman/adlc/(?:blob|tree)/main(?:/|\))")
    wrong_release = re.compile(r"https://github\.com/bigeasyfreeman/adlc/(?:blob|tree)/(v[^/]+)/")
    for source in published_sources:
        source_text = source.read_text(encoding="utf-8")
        if mutable_source.search(source_text):
            failures.append(f"{source.relative_to(ROOT)}: mutable main source link in versioned docs")
        for linked_tag in wrong_release.findall(source_text):
            if linked_tag != release_tag:
                failures.append(f"{source.relative_to(ROOT)}: source link uses {linked_tag}, expected {release_tag}")

    docs_workflow = (ROOT / ".github/workflows/docs.yml").read_text(encoding="utf-8")
    for token in (
        "tags: [\"v*\"]",
        "check_docs_release.py",
        "check_docs_viewports.py",
    ):
        if token not in docs_workflow:
            failures.append(f"docs validation workflow missing {token}")
    for forbidden in ("workflow_dispatch:", "actions/deploy-pages@v4"):
        if forbidden in docs_workflow:
            failures.append(f"docs validation workflow exposes publication token {forbidden}")
    release_workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    for token in (
        "workflow_dispatch:",
        "confirm_publication:",
        "approval_record_json:",
        "--target pages_deploy",
        "environment: github-pages",
        "actions/deploy-pages@v4",
        "check_docs_release.py",
        "check_docs_viewports.py",
    ):
        if token not in release_workflow:
            failures.append(f"packet-approved Pages workflow missing {token}")
    if re.search(r"google-analytics|googletagmanager|plausible", "\n".join(path.read_text(encoding="utf-8") for path in site.rglob("*.html")), re.I):
        failures.append("analytics present without privacy approval")

    release = subprocess.run(
        [sys.executable, "scripts/check_docs_release.py", "--tag", release_tag, "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if release.returncode or json.loads(release.stdout).get("status") != "pass":
        failures.append("release/version dry-run failed")

    if failures:
        print("built docs failures:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print(f"built docs: pass ({len(REQUIRED_LOCATIONS)} pages, version {docs_version}, deployment approval-bound)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
