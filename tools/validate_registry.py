from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from registry_lib import ROOT, build_jsonld, build_public_manifest, build_sitemap, entity_map, load_registry


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def valid_https(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate_source() -> list[str]:
    errors: list[str] = []
    registry = load_registry()
    entities_list = registry["entities"]["entities"]
    ids = [item["id"] for item in entities_list]
    if len(ids) != len(set(ids)):
        fail("duplicate entity IDs", errors)
    entities = entity_map(registry)

    for entity in entities_list:
        if not re.fullmatch(r"[a-z][a-z0-9-]*:[a-z0-9-]+", entity["id"]):
            fail(f"invalid entity ID: {entity['id']}", errors)
        if not valid_https(entity["canonical_url"]):
            fail(f"non-HTTPS canonical URL: {entity['id']}", errors)
        for rel in entity.get("relationships", []):
            if rel["target"] not in entities:
                fail(f"dangling relationship {entity['id']} -> {rel['target']}", errors)

    identity = registry["identity"]
    for key in ("canonical_person", "canonical_artist", "canonical_domain"):
        if identity[key] not in entities:
            fail(f"identity.{key} references unknown entity {identity[key]}", errors)

    platforms = registry["platforms"]["platforms"]
    platform_ids = [item["id"] for item in platforms]
    if len(platform_ids) != len(set(platform_ids)):
        fail("duplicate platform IDs", errors)
    for platform in platforms:
        if platform["owner_entity"] not in entities:
            fail(f"platform owner missing: {platform['id']}", errors)
        if not valid_https(platform["url"]):
            fail(f"platform URL must be HTTPS: {platform['id']}", errors)

    catalog = registry["catalog"]
    if catalog["artist"] not in entities:
        fail("catalog artist references unknown entity", errors)
    release_ids = [item["id"] for item in catalog["releases"]]
    if len(release_ids) != len(set(release_ids)):
        fail("duplicate release IDs", errors)
    for release in catalog["releases"]:
        if not 2000 <= int(release["year"]) <= 2100:
            fail(f"invalid release year: {release['id']}", errors)
        if not valid_https(release["url"]):
            fail(f"release URL must be HTTPS: {release['id']}", errors)

    profile = registry["profile"]
    if profile["canonical_domain"] != "https://iambandobandz.com/":
        fail("canonical domain drift detected", errors)
    paths = [r["path"] for r in profile["routes"]]
    if len(paths) != len(set(paths)):
        fail("duplicate public routes", errors)
    if "/" not in paths or "/privacy/" not in paths or "/terms/" not in paths:
        fail("required public routes missing", errors)

    capture = profile.get("lead_capture")
    if not isinstance(capture, dict):
        fail("profile.lead_capture must be an object", errors)
    else:
        if not isinstance(capture.get("api_enabled"), bool):
            fail("lead_capture.api_enabled must be boolean", errors)
        endpoint = str(capture.get("api_endpoint", "")).strip()
        if not valid_https(endpoint):
            fail("lead_capture.api_endpoint must be HTTPS", errors)
        if capture.get("fallback") != "formsubmit":
            fail("lead_capture fallback must remain formsubmit until private runtime cutover is complete", errors)
        if capture.get("consent_text_version") != "signal-capture-v1":
            fail("lead_capture consent text version drift detected", errors)

    private_dir = ROOT / "registry" / "private"
    allowed_private = {".gitignore", "README.md"}
    leaked = [p.name for p in private_dir.iterdir() if p.name not in allowed_private]
    if leaked:
        fail(f"private data boundary violation: {', '.join(sorted(leaked))}", errors)

    build_jsonld(registry)
    build_public_manifest(registry)
    build_sitemap(registry)
    return errors


def validate_built_site(site: Path) -> list[str]:
    errors: list[str] = []
    registry = load_registry()
    required = ["index.html", "sitemap.xml", "privacy/index.html", "terms/index.html", ".well-known/iambandobandz.json", "identity.jsonld"]
    for relative in required:
        if not (site / relative).is_file():
            fail(f"built site missing {relative}", errors)
    if errors:
        return errors

    index = (site / "index.html").read_text(encoding="utf-8")
    if "Privacy" not in index or "Terms" not in index:
        fail("homepage missing legal links", errors)
    jsonld = json.dumps(build_jsonld(registry), separators=(",", ":"), ensure_ascii=False)
    if jsonld not in index:
        fail("homepage JSON-LD is not registry-generated", errors)

    capture = registry["profile"]["lead_capture"]
    meta_name = 'name="iambandobandz:lead-api-endpoint"'
    if capture["api_enabled"] is True:
        if meta_name not in index or capture["api_endpoint"] not in index:
            fail("enabled lead API endpoint was not injected into built homepage", errors)
    elif meta_name in index:
        fail("disabled lead API leaked into built homepage", errors)

    script = (site / "script.js").read_text(encoding="utf-8")
    if "iambandobandz:lead-api-endpoint" not in script:
        fail("site script is not cutover-aware", errors)
    if "https://formsubmit.co/ajax/bandobandz440@gmail.com" not in script:
        fail("FormSubmit fallback was removed before private runtime verification", errors)
    if "signal-capture-v1" not in script:
        fail("site consent version is not pinned", errors)

    portfolio = (site / "portfolio" / "index.html").read_text(encoding="utf-8")
    if "massivemagnetics.github.io/portfolio" in portfolio:
        fail("portfolio canonical drift remains", errors)
    if "chatgpt.site" in portfolio:
        fail("portfolio still depends on chatgpt.site social image", errors)
    if "https://iambandobandz.com/portfolio/" not in portfolio:
        fail("portfolio canonical URL missing", errors)

    sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")
    if sitemap != build_sitemap(registry):
        fail("built sitemap differs from canonical registry", errors)

    public_manifest = json.loads((site / ".well-known" / "iambandobandz.json").read_text(encoding="utf-8"))
    if public_manifest != build_public_manifest(registry):
        fail("public manifest differs from canonical registry", errors)

    if (site / "registry" / "private").exists():
        fail("private registry boundary leaked into Pages artifact", errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate canonical IAMBANDOBANDZ registry and optional Pages artifact")
    parser.add_argument("--site", type=Path, help="Validate a built Pages directory")
    args = parser.parse_args()

    errors = validate_source()
    if args.site:
        errors.extend(validate_built_site(args.site))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Registry validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())