#!/usr/bin/env python3
"""Build B Heard Network as an independent static-site root.

This builder only copies and rewrites local source files. It does not call
external services, provision resources, modify DNS, or deploy anything.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://bheardnetwork.com"

COPY_FILES = (
    ("beheardnetwork/index.html", "index.html"),
    ("network/index.html", "network/index.html"),
    ("network/board/index.html", "network/board/index.html"),
    ("network/board/board.css", "network/board/board.css"),
    ("network/board/board.js", "network/board/board.js"),
    ("network/thanks/index.html", "network/thanks/index.html"),
    ("network/offer.json", "network/offer.json"),
    ("styles.css", "styles.css"),
    ("beheardnetwork/brand.css", "brand.css"),
    ("beheardnetwork/analytics.js", "analytics.js"),
    ("beheardnetwork/_headers", "_headers"),
    ("beheardnetwork/assets/bheard-network-logo.svg", "assets/bheard-network-logo.svg"),
)

CANONICAL_URLS = {
    "index.html": f"{ORIGIN}/",
    "network/index.html": f"{ORIGIN}/network/",
    "network/board/index.html": f"{ORIGIN}/network/board/",
}

HOME_WORDMARK = (
    '<a class="wordmark" href="/" aria-label="IAMBANDOBANDZ home">B HEARD NETWORK</a>'
)
BOARD_WORDMARK = (
    '<a class="wordmark" href="/network/" aria-label="B Heard Network home">B HEARD NETWORK</a>'
)
INDEPENDENT_WORDMARK = (
    '<a class="wordmark" href="/" aria-label="B Heard Network home">'
    '<img class="bheard-logo" src="/assets/bheard-network-logo.svg" alt="">'
    '<span>B HEARD NETWORK</span></a>'
)


def replace_once(value: str, old: str, new: str, label: str) -> str:
    count = value.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one exact source anchor, found {count}")
    return value.replace(old, new, 1)


def copy_source(source_relative: str, destination: Path) -> None:
    source = ROOT / source_relative
    if not source.is_file():
        raise FileNotFoundError(f"required B Heard source missing: {source_relative}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def rewrite_page(source_relative: str, destination_relative: str, output: Path) -> None:
    source = ROOT / source_relative
    page = source.read_text(encoding="utf-8")

    canonical = CANONICAL_URLS.get(destination_relative)
    if canonical:
        pattern = re.compile(r'<link rel="canonical" href="[^"]+"\s*/?>')
        page, count = pattern.subn(
            f'<link rel="canonical" href="{canonical}">', page, count=1
        )
        if count != 1:
            raise RuntimeError(f"{source_relative}: canonical link missing or ambiguous")

    if source_relative in ("beheardnetwork/index.html", "network/index.html"):
        page = replace_once(page, HOME_WORDMARK, INDEPENDENT_WORDMARK, source_relative)
    elif source_relative == "network/board/index.html":
        page = replace_once(page, BOARD_WORDMARK, INDEPENDENT_WORDMARK, source_relative)

    # B Heard remains the destination root. Artist/Empire surfaces are explicit
    # cross-site links, never accidental root-relative paths on the B Heard host.
    page = page.replace('<a href="/">Empire</a>', '<a href="https://iambandobandz.com/">Empire</a>')
    page = page.replace('href="/store/"', 'href="https://iambandobandz.com/store/"')
    page = page.replace('href="/proof/"', 'href="https://iambandobandz.com/proof/"')
    page = page.replace('href="/privacy/"', 'href="https://iambandobandz.com/privacy/"')
    page = page.replace('href="/terms/"', 'href="https://iambandobandz.com/terms/"')
    page = page.replace(
        'href="/">IAMBANDOBANDZ HOME</a>',
        'href="https://iambandobandz.com/">IAMBANDOBANDZ HOME</a>',
    )

    # The source count was not independently verified. Do not publish it as fact.
    page = page.replace("a 20,000-member artist community", "a community for independent artists")
    page = page.replace("A 20,000-member artist community", "A community for independent artists")
    page = page.replace("20,000-member artist community", "independent-artist community")

    styles_tag = '<link rel="stylesheet" href="/styles.css">'
    if styles_tag not in page:
        raise RuntimeError(f"{source_relative}: shared stylesheet reference missing")
    if 'href="/brand.css"' not in page:
        page = page.replace(
            styles_tag,
            styles_tag + '\n  <link rel="stylesheet" href="/brand.css">',
            1,
        )

    if source_relative == "network/thanks/index.html":
        brand = (
            '<div class="wordmark bheard-return-brand">'
            '<img class="bheard-logo" src="/assets/bheard-network-logo.svg" alt="">'
            '<span>B HEARD NETWORK</span></div>\n  '
        )
        page = replace_once(
            page,
            '<p class="eyebrow">B HEARD NETWORK / CHECKOUT RETURN</p>',
            brand + '<p class="eyebrow">B HEARD NETWORK / CHECKOUT RETURN</p>',
            "checkout return brand",
        )

    if 'src="/analytics.js"' not in page:
        page = replace_once(
            page,
            "</body>",
            '<script src="/analytics.js" defer></script>\n</body>',
            f"{source_relative} analytics script",
        )

    destination = output / destination_relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(page, encoding="utf-8")


def build(output: Path) -> Path:
    """Build a marked output directory without deleting unrecognized data."""
    raw_output = Path(output).expanduser()
    if raw_output.is_symlink():
        raise RuntimeError(f"refusing symlink output directory: {raw_output}")
    output = raw_output.resolve()
    if output == ROOT or output in ROOT.parents:
        raise RuntimeError(f"refusing unsafe output path: {output}")
    if ROOT in output.parents and (ROOT / "dist") not in output.parents:
        raise RuntimeError("repository-local output must be inside dist/")

    marker = output / ".bheard-build"
    marker_text = (
        "Generated by tools/build_bheard_site.py. Safe to replace on the next build.\n"
    )
    if output.exists():
        if not marker.is_file() or marker.read_text(encoding="utf-8") != marker_text:
            raise RuntimeError(
                f"refusing to replace unmarked output directory: {output}"
            )
        shutil.rmtree(output)

    output.mkdir(parents=True)
    for source_relative, destination_relative in COPY_FILES:
        if source_relative.endswith(".html"):
            rewrite_page(source_relative, destination_relative, output)
        else:
            copy_source(source_relative, output / destination_relative)

    offer_path = output / "network" / "offer.json"
    offer = json.loads(offer_path.read_text(encoding="utf-8"))
    if offer.get("offer_code") != "bheard_creator_promo_v1":
        raise RuntimeError("unexpected B Heard offer code; refusing to rewrite registry")
    offer["canonical_path"] = f"{ORIGIN}/network/"
    offer_path.write_text(json.dumps(offer, indent=2) + "\n", encoding="utf-8")

    (output / "robots.txt").write_text(
        "User-agent: *\nAllow: /\nDisallow: /network/thanks/\n",
        encoding="utf-8",
    )
    marker.write_text(marker_text, encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "dist" / "bheardnetwork",
        help="generated output directory (default: dist/bheardnetwork)",
    )
    args = parser.parse_args()
    try:
        output = build(args.output)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(1, f"B Heard site build failed: {exc}\n")
    print(f"B Heard independent static root built at {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
