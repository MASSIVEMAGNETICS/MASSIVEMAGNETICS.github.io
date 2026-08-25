from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path

from registry_lib import ROOT, build_jsonld, build_public_manifest, build_sitemap, load_registry

COPY_ITEMS = [
    ".nojekyll",
    "CNAME",
    "analytics.js",
    "favicon.svg",
    "index.html",
    "audit",
    "jesus-told-me",
    "network",
    "owner",
    "portfolio",
    "privacy",
    "proof",
    "research",
    "signal",
    "robots.txt",
    "script.js",
    "site.webmanifest",
    "llms.txt",
    "social-card.svg",
    "social-card.webp",
    "store",
    "styles.css",
    "terms",
]

ANALYTICS_PAGES = [
    "audit/index.html",
    "network/index.html",
    "proof/index.html",
    "research/index.html",
    "signal/index.html",
    "store/index.html",
]


def copy_item(source: Path, destination: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def inject_legal_links(path: Path) -> None:
    page = path.read_text(encoding="utf-8")
    if 'href="/privacy/"' in page and 'href="/terms/"' in page:
        return
    legal = '<span data-legal-links="registry"><a href="/privacy/">Privacy</a> · <a href="/terms/">Terms</a> · <a href="/proof/">Proof</a></span>'
    if "</footer>" not in page:
        raise RuntimeError(f"commercial page footer missing: {path.relative_to(path.parents[1])}")
    path.write_text(page.replace("</footer>", legal + "</footer>", 1), encoding="utf-8")


def inject_analytics_script(path: Path) -> None:
    page = path.read_text(encoding="utf-8")
    if 'src="/analytics.js"' in page:
        return
    if "</body>" not in page:
        raise RuntimeError(f"analytics target missing body close: {path}")
    page = page.replace("</body>", '<script src="/analytics.js" defer></script>\n</body>', 1)
    path.write_text(page, encoding="utf-8")


def inject_owner_analytics_link(path: Path) -> None:
    page = path.read_text(encoding="utf-8")
    if 'href="/owner/analytics/"' in page:
        return
    anchor = '<button class="btn" data-action="reference">WHAT THIS MEANS</button>'
    if anchor not in page:
        raise RuntimeError("owner control plane analytics insertion anchor missing")
    page = page.replace(anchor, anchor + '<a class="btn" href="/owner/analytics/">ANALYTICS</a>', 1)
    path.write_text(page, encoding="utf-8")


def normalize_homepage_identity(index: str) -> str:
    """Normalize the public homepage to the canonical brand/search contract.

    Uppercase IAMBANDOBANDZ remains acceptable as visual styling. The semantic
    identity token emitted to crawlers and structured data is iambandobandz.
    """
    index = re.sub(
        r"<title>.*?</title>",
        "<title>iambandobandz — Official Site | The Signal Survives</title>",
        index,
        count=1,
        flags=re.DOTALL,
    )
    index = re.sub(
        r'<meta name="description"[^>]*>',
        '<meta name="description" content="Official website of iambandobandz: independent Rust Belt hip-hop, B Heard Network, Massive Magnetics, public proof, research, and direct music ownership.">',
        index,
        count=1,
    )
    index = re.sub(r'\s*<meta name="keywords"[^>]*>\s*', "\n", index, count=1)
    index = re.sub(
        r'<meta property="og:site_name"[^>]*>',
        '<meta property="og:site_name" content="iambandobandz">',
        index,
        count=1,
    )
    index = re.sub(
        r'<meta property="og:title"[^>]*>',
        '<meta property="og:title" content="iambandobandz — The Signal Survives">',
        index,
        count=1,
    )
    index = re.sub(
        r'<meta name="twitter:title"[^>]*>',
        '<meta name="twitter:title" content="iambandobandz — The Signal Survives">',
        index,
        count=1,
    )
    index = index.replace('aria-label="IAMBANDOBANDZ home"', 'aria-label="iambandobandz home"')
    index = index.replace('<p class="eyebrow">“I AM BANDO BANDZ”</p>', '<p class="eyebrow">iambandobandz</p>')

    old_nav = '<a href="/signal/">Signal</a><a href="#listen">Listen</a><a href="#empire">Empire</a><a href="/proof/">Proof</a><a href="/research/">Research</a><a href="#contact">Contact</a>'
    new_nav = '<a href="#listen">Listen</a><a href="/store/">Store</a><a href="/network/">Creators</a><a href="/proof/">Proof</a><a href="/research/">Lab</a><a href="#contact">Contact</a>'
    index = index.replace(old_nav, new_nav)

    old_header_cta = '<a class="header-cta" href="/audit/" data-revenue-path="truth-compiler" data-loop-stage="consider">Inspect $97 audit</a>'
    new_header_cta = '<a class="header-cta" href="/store/" data-revenue-path="store" data-loop-stage="buy">Own the music</a>'
    index = index.replace(old_header_cta, new_header_cta)

    old_hero_actions = '<div class="hero-actions"><a class="button button-primary" href="/audit/" data-revenue-path="truth-compiler" data-loop-stage="consider">See the $97 repo audit →</a><a class="button button-ghost" href="/store/" data-revenue-path="store" data-loop-stage="buy">Own the music →</a></div>'
    new_hero_actions = '<div class="hero-actions"><a class="button button-primary" href="https://www.youtube.com/channel/UCIaEOclqKUzIVPfkEuGzEEQ" target="_blank" rel="noopener noreferrer" data-music-platform="youtube">Listen on YouTube →</a><a class="button button-ghost" href="/store/" data-revenue-path="store" data-loop-stage="buy">Own the music →</a></div>'
    index = index.replace(old_hero_actions, new_hero_actions)

    index = index.replace('<dt>Artist identity</dt><dd>IAMBANDOBANDZ</dd>', '<dt>Artist identity</dt><dd>iambandobandz</dd>')
    index = index.replace('<p class="lead">IAMBANDOBANDZ is Brandon Emery:', '<p class="lead">iambandobandz is Brandon Emery:')
    index = index.replace('<article><span>HUMAN SIGNAL / 01</span><h3>IAMBANDOBANDZ</h3>', '<article><span>HUMAN SIGNAL / 01</span><h3>iambandobandz</h3>')
    index = index.replace('<footer><strong>IAMBANDOBANDZ</strong>', '<footer><strong>iambandobandz</strong>')

    if "Bando Bandz" in index or "I AM BANDO BANDZ" in index:
        raise RuntimeError("legacy artist alias leaked into built homepage")
    return index


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
    index = normalize_homepage_identity(index)

    # Keep the proof surface reachable from the canonical homepage without
    # forcing the source homepage to duplicate deployment-only routing logic.
    if 'href="/proof/"' not in index:
        proof_nav_anchor = '<a href="#empire">Empire</a>'
        if proof_nav_anchor not in index:
            raise RuntimeError("homepage Empire nav anchor not found for Proof Ledger injection")
        index = index.replace(proof_nav_anchor, proof_nav_anchor + '<a href="/proof/">Proof</a>', 1)

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

    # Commercial pages must expose the same trust boundary even when their
    # source templates evolve independently.
    inject_legal_links(output / "store" / "index.html")
    inject_legal_links(output / "network" / "index.html")

    # Shared local-first analytics uses one event schema across major public
    # surfaces. A future HTTPS collector can ingest the same payloads without
    # rewriting the owner dashboard.
    for relative in ANALYTICS_PAGES:
        inject_analytics_script(output / relative)

    # Owner surfaces remain noindex and static; code is public, owner data is
    # local-browser only until a real authenticated backend exists.
    inject_owner_analytics_link(output / "owner" / "index.html")

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


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a sanitized GitHub Pages artifact from the canonical registry")
    parser.add_argument("--output", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    build(args.output.resolve())
    print(f"Built Pages artifact: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
