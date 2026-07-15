#!/usr/bin/env python3
"""Render the built documentation at desktop and mobile viewports."""

from __future__ import annotations

import argparse
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    failures: list[str] = []

    with tempfile.TemporaryDirectory(prefix="adlc-docs-preview-") as server_root:
        (Path(server_root) / "adlc").symlink_to(site, target_is_directory=True)
        handler = partial(QuietHandler, directory=server_root)
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f"http://127.0.0.1:{server.server_port}"

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                for name, width, height in (("desktop", 1280, 800), ("mobile", 390, 844)):
                    page = browser.new_page(viewport={"width": width, "height": height})
                    console_errors: list[str] = []
                    http_errors: list[str] = []
                    page.on(
                        "console",
                        lambda message: console_errors.append(message.text)
                        if message.type == "error" and not message.text.startswith("Failed to load resource:")
                        else None,
                    )
                    page.on(
                        "response",
                        lambda response: http_errors.append(f"{response.status} {response.url}")
                        if response.status >= 400 and response.url.startswith(origin)
                        else None,
                    )

                    for route, heading in (("/adlc/", "ADLC documentation"), ("/adlc/start/first-fix/", "First Fix loop")):
                        page.goto(f"{origin}{route}", wait_until="networkidle")
                        metrics = page.evaluate(
                            """() => {
                              const main = document.querySelector('main');
                              const heading = document.querySelector('h1');
                              const mainRect = main?.getBoundingClientRect();
                              return {
                                overflow: document.documentElement.scrollWidth - window.innerWidth,
                                mainVisible: !!mainRect && mainRect.width > 0 && mainRect.right <= window.innerWidth + 1,
                                headingVisible: !!heading && heading.getBoundingClientRect().height > 0,
                                searchLabel: document.querySelector('input[aria-label="Search"]')?.getAttribute('aria-label'),
                              };
                            }"""
                        )
                        context = f"{name} {route}"
                        if metrics["overflow"] > 1:
                            failures.append(f"{context}: horizontal overflow is {metrics['overflow']}px")
                        if not metrics["mainVisible"] or not metrics["headingVisible"]:
                            failures.append(f"{context}: main content or heading is not visible within viewport")
                        if metrics["searchLabel"] != "Search":
                            failures.append(f"{context}: accessible search input missing")
                        if not page.locator("main h1").inner_text().strip().startswith(heading):
                            failures.append(f"{context}: expected heading {heading!r} did not render")
                        if console_errors:
                            failures.append(f"{context}: console errors: {'; '.join(console_errors)}")
                        if http_errors:
                            failures.append(f"{context}: HTTP errors: {'; '.join(http_errors)}")
                        console_errors.clear()
                        http_errors.clear()
                        if route == "/adlc/":
                            page.screenshot(path=output / f"home-{name}.png", full_page=True)
                    page.close()
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

    if failures:
        print("viewport failures:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"docs viewports: pass (desktop 1280x800, mobile 390x844; captures in {args.output})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
