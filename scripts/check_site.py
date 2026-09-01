from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from struct import unpack
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent.parent
REQUIRED = {
    "index.html",
    "privacy.html",
    "terms.html",
    "support.html",
    "deletion.html",
    "styles.css",
    "robots.txt",
    "sitemap.xml",
    "assets/channel-hero.png",
    "assets/workflow-still.png",
}
FORBIDDEN_TEXT = ("—", "–", "TODO", "Lorem ipsum", "Jane Doe", "Acme")


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.images: list[dict[str, str | None]] = []
        self.ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"] or "")
        if tag == "a" and values.get("href"):
            self.links.append(values["href"] or "")
        if tag == "img":
            self.images.append(values)


def validate_page(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for marker in FORBIDDEN_TEXT:
        if marker in text:
            raise AssertionError(f"{path.name}: forbidden visible marker {marker!r}")
    parser = PageParser()
    parser.feed(text)
    if len(parser.ids) != len(set(parser.ids)):
        raise AssertionError(f"{path.name}: duplicate element id")
    for link in parser.links:
        if link.startswith(("#", "mailto:")):
            continue
        parsed = urlparse(link)
        if parsed.scheme:
            if parsed.scheme != "https":
                raise AssertionError(f"{path.name}: external link must use HTTPS: {link}")
            continue
        target = ROOT / parsed.path
        if not target.exists():
            raise AssertionError(f"{path.name}: missing local link target: {link}")
    for image in parser.images:
        source = image.get("src")
        alt = image.get("alt")
        if not source or alt is None or not alt.strip():
            raise AssertionError(f"{path.name}: image missing source or meaningful alt text")
        if not (ROOT / source).is_file():
            raise AssertionError(f"{path.name}: missing image: {source}")


def main() -> None:
    missing = sorted(path for path in REQUIRED if not (ROOT / path).exists())
    if missing:
        raise AssertionError(f"Missing site files: {missing}")
    for page in sorted(ROOT.glob("*.html")):
        validate_page(page)
    for image_path in (ROOT / "assets").glob("*.png"):
        header = image_path.read_bytes()[:24]
        if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
            raise AssertionError(f"Invalid PNG: {image_path.name}")
        width, height = unpack(">II", header[16:24])
        if width < 1200 or height < 700:
            raise AssertionError(f"Image is too small: {image_path.name} {(width, height)}")
    css = (ROOT / "styles.css").read_text(encoding="utf-8")
    for required_css in ("100dvh", "prefers-reduced-motion", "focus-visible", "prefers-color-scheme"):
        if required_css not in css:
            raise AssertionError(f"Missing CSS safeguard: {required_css}")
    print("Site checks passed")


if __name__ == "__main__":
    main()
