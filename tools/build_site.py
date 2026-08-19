from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path

from registry_lib import (
    ROOT,
    build_autopoiesis_manifest,
    build_jsonld,
    build_public_manifest,
    build_sitemap,
    load_registry,
)

COPY_ITEMS = [
    ".nojekyll",
    "CNAME",
    "favicon.svg",
    "index.html",
    "audit",
    "jesus-told-me",
    "network",
    "portfolio",
    "privacy",
    "research",
    "robots.txt",
    "script.js",
    "autopoietic-runtime.js",
    "sw.js",
    "site.webmanifest",
    "social-card.svg",
    "social-card.webp",
    "store",
    "styles.css",
    "terms",
]


def copy_item(source: Path, destination: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def inject_autopoietic_runtime(output: Path) -> None:
    runtime_tag = '<script src="/autopoietic-runtime.js" defer></script>'
    for page in output.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        if runtime_tag in text:
            continue
        if "</body>" not in text:
            raise RuntimeError(f"HTML page cannot receive autopoietic runtime: {page.relative_to(output)}")
        text = text.replace("</body>", f"  {runtime_tag}\n</body>", 1)
        page.write_text(text, encoding="utf-8")


def build(output: Path) -> None:
    registry = load_registry()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    for item in COPY_ITEMS:
        source = ROOT / item
        if not source.exists():
            raise FileNotFoundError(f"required deploy source missing: {item}")
        copy_item(source, output / item)

    # Publish only the explicitly public registry partition.
    shutil.copytree(ROOT / "registry" / "public", output / "registry" / "public")

    compact_jsonld = json.dumps(build_jsonld(registry), separators=(",", ":"), ensure_ascii=False)
    pretty_jsonld = json.dumps(build_jsonld(registry), indent=2, ensure_ascii=False) + "\n"
    (output / "identity.jsonld").write_text(pretty_jsonld, encoding="utf-8")

    index_path = output / "index.html"
    index = index_path.read_text(encoding="utf-8")
    script_pattern = re.compile(r'<script type="application/ld\+json">.*?</script>', re.DOTALL)
    replacement = f'<script type="application/ld+json">{compact_jsonld}</script>'
    if not script_pattern.search(index):
        raise RuntimeError("homepage JSON-LD block not found")
    index = script_pattern.sub(replacement, index, count=1)

    # Keep the revenue path on the same verified Pages origin. The separate
    # .store domain can be a vanity redirect later, but it is not a launch dependency.
    index = index.replace("https://iambandobandz.store/", "/store/")

    profile = registry["profile"]
    capture = profile.get("lead_capture", {})
    if capture.get("api_enabled") is True:
        endpoint = str(capture.get("api_endpoint", "")).strip()
        if not endpoint.startswith("https://"):
            raise RuntimeError("enabled lead API must use HTTPS")
        meta = (
            '<meta name="iambandobandz:lead-api-endpoint" '
            f'content="{html.escape(endpoint, quote=True)}">'
        )
        if 'name="iambandobandz:lead-api-endpoint"' not in index:
            index = index.replace("</head>", f"  {meta}\n</head>", 1)
    else:
        index = re.sub(
            r'\s*<meta name="iambandobandz:lead-api-endpoint"[^>]*>\s*',
            "\n",
            index,
        )

    if 'data-legal-links="registry"' not in index:
        legal = '<span data-legal-links="registry"><a href="/privacy/">Privacy</a> · <a href="/terms/">Terms</a></span>'
        index = index.replace("</footer>", legal + "</footer>", 1)
    index_path.write_text(index, encoding="utf-8")

    portfolio_path = output / "portfolio" / "index.html"
    portfolio = portfolio_path.read_text(encoding="utf-8")
    portfolio = portfolio.replace("https://massivemagnetics.github.io/portfolio/", "https://iambandobandz.com/portfolio/")
    portfolio = re.sub(r"https://[^\"']+\.chatgpt\.site/cognitive-network-hero\.png", "https://iambandobandz.com/social-card.webp", portfolio)
    portfolio_path.write_text(portfolio, encoding="utf-8")

    (output / "sitemap.xml").write_text(build_sitemap(registry), encoding="utf-8")
    well_known = output / ".well-known"
    well_known.mkdir(exist_ok=True)
    (well_known / "iambandobandz.json").write_text(
        json.dumps(build_public_manifest(registry), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (well_known / "autopoiesis.json").write_text(
        json.dumps(build_autopoiesis_manifest(registry), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Every rendered page receives the same boundary/continuity runtime.
    inject_autopoietic_runtime(output)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a sanitized GitHub Pages artifact from the canonical registry")
    parser.add_argument("--output", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    build(args.output.resolve())
    print(f"Built Pages artifact: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
