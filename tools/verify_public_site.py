from __future__ import annotations

import argparse
import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


USER_AGENT = "iambandobandz-public-verifier/1.0"
REQUIRED_SITEMAP_ROUTES = {
    "/",
    "/proof/",
    "/audit/",
    "/research/",
    "/signal/",
    "/store/",
    "/network/",
    "/frontier-radar/",
    "/portfolio/",
    "/jesus-told-me/",
    "/privacy/",
    "/terms/",
}


def fetch_text(url: str, timeout: int = 20) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed owner-controlled URLs
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}: {url}")
        return response.read().decode("utf-8")


def verify(base_url: str) -> list[str]:
    errors: list[str] = []
    base = base_url.rstrip("/") + "/"

    def get(path: str) -> str:
        return fetch_text(urljoin(base, path.lstrip("/")))

    try:
        home = get("/")
    except Exception as exc:  # noqa: BLE001 - verifier reports all transport failures
        return [f"homepage unavailable: {exc}"]

    if "<title>iambandobandz — Official Site" not in home:
        errors.append("homepage title does not lead with canonical iambandobandz")
    if '<link rel="canonical" href="https://iambandobandz.com/">' not in home:
        errors.append("homepage canonical URL is missing or incorrect")
    if '<meta property="og:site_name" content="iambandobandz">' not in home:
        errors.append("homepage Open Graph site name is not canonical")
    if "Bando Bandz" in home or "I AM BANDO BANDZ" in home:
        errors.append("legacy artist alias leaked into public homepage")

    try:
        robots = get("/robots.txt")
        if "Sitemap: https://iambandobandz.com/sitemap.xml" not in robots:
            errors.append("robots.txt does not advertise canonical sitemap")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"robots.txt unavailable: {exc}")

    try:
        sitemap = get("/sitemap.xml")
        for path in REQUIRED_SITEMAP_ROUTES:
            expected = base.rstrip("/") + path
            if expected not in sitemap:
                errors.append(f"sitemap missing {expected}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"sitemap unavailable: {exc}")

    try:
        manifest = json.loads(get("/site.webmanifest"))
        if manifest.get("short_name") != "iambandobandz":
            errors.append("web manifest short_name is not canonical")
        if manifest.get("start_url") != "/" or manifest.get("scope") != "/":
            errors.append("web manifest origin scope drift detected")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"site.webmanifest invalid or unavailable: {exc}")

    try:
        graph = json.loads(get("/identity.jsonld"))
        nodes = graph.get("@graph", [])
        artist_nodes = [node for node in nodes if node.get("@type") == "MusicGroup"]
        if len(artist_nodes) != 1 or artist_nodes[0].get("name") != "iambandobandz":
            errors.append("identity.jsonld does not expose exactly one canonical iambandobandz MusicGroup")
        if "Bando Bandz" in json.dumps(graph, ensure_ascii=False):
            errors.append("legacy artist alias leaked into identity.jsonld")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"identity.jsonld invalid or unavailable: {exc}")

    try:
        public_manifest = json.loads(get("/.well-known/iambandobandz.json"))
        if public_manifest.get("canonical_brand") != "iambandobandz":
            errors.append("well-known manifest canonical_brand mismatch")
        if public_manifest.get("canonical_domain") != "https://iambandobandz.com/":
            errors.append("well-known manifest canonical_domain mismatch")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"well-known identity manifest invalid or unavailable: {exc}")

    try:
        llms = get("/llms.txt")
        if "Canonical artist/brand: iambandobandz" not in llms:
            errors.append("llms.txt canonical artist declaration missing")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"llms.txt unavailable: {exc}")

    try:
        portfolio = get("/portfolio/")
        if "massivemagnetics.github.io/portfolio" in portfolio:
            errors.append("portfolio canonical still points to GitHub Pages hostname")
        if "chatgpt.site" in portfolio:
            errors.append("portfolio still depends on chatgpt.site social metadata")
        if 'https://iambandobandz.com/portfolio/' not in portfolio:
            errors.append("portfolio canonical iambandobandz.com URL missing")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"portfolio unavailable: {exc}")

    try:
        radar = get("/frontier-radar/")
        if '<link rel="canonical" href="https://iambandobandz.com/frontier-radar/">' not in radar:
            errors.append("Frontier Radar canonical URL missing")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Frontier Radar unavailable: {exc}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the deployed iambandobandz public search/identity contract")
    parser.add_argument("--base-url", default="https://iambandobandz.com/")
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--delay", type=float, default=10.0)
    args = parser.parse_args()

    retries = max(1, args.retries)
    final_errors: list[str] = []
    for attempt in range(1, retries + 1):
        try:
            final_errors = verify(args.base_url)
        except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
            final_errors = [str(exc)]
        if not final_errors:
            print("Public site verification: PASS")
            return 0
        if attempt < retries:
            print(f"Attempt {attempt}/{retries} failed; retrying in {args.delay:.0f}s...", file=sys.stderr)
            time.sleep(max(0.0, args.delay))

    for error in final_errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
