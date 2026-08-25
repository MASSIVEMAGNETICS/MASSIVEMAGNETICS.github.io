from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "registry" / "public"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_registry() -> dict[str, Any]:
    return {
        "entities": load_json(PUBLIC / "entities.json"),
        "identity": load_json(PUBLIC / "identity.json"),
        "platforms": load_json(PUBLIC / "platforms.json"),
        "catalog": load_json(PUBLIC / "catalog.json"),
        "profile": load_json(PUBLIC / "public-profile.json"),
    }


def entity_map(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in registry["entities"]["entities"]}


def build_jsonld(registry: dict[str, Any]) -> dict[str, Any]:
    entities = entity_map(registry)
    identity = registry["identity"]
    platforms = registry["platforms"]["platforms"]
    person = entities[identity["canonical_person"]]
    artist = entities[identity["canonical_artist"]]
    origin = identity["origin"]
    contacts = identity["public_contacts"]

    person_node: dict[str, Any] = {
        "@type": "Person",
        "@id": "https://iambandobandz.com/#brandon-emery",
        "name": person["name"],
        "url": person["canonical_url"],
        "email": f"mailto:{contacts['artist_email']}",
        "telephone": contacts["phone"],
        "address": {
            "@type": "PostalAddress",
            "addressLocality": origin["locality"],
            "addressRegion": origin["region"],
            "addressCountry": origin["country"],
        },
        "sameAs": [p["url"] for p in platforms if p["owner_entity"] in {person["id"], "lab:massive-magnetics"}],
    }
    if person.get("aliases"):
        person_node["alternateName"] = person["aliases"]

    same_as_artist = [p["url"] for p in platforms if p["owner_entity"] == artist["id"]]
    artist_node: dict[str, Any] = {
        "@type": "MusicGroup",
        "@id": "https://iambandobandz.com/#iambandobandz",
        "name": artist["name"],
        "url": artist["canonical_url"],
        "description": "Independent Rust Belt hip-hop artist and the canonical music identity represented by iambandobandz.com.",
        "genre": ["Hip-Hop", "Rap", "Rust Belt Hip-Hop"],
        "foundingLocation": {"@type": "Place", "name": "Lorain, Ohio"},
        "sameAs": same_as_artist,
        "mainEntityOfPage": {"@id": "https://iambandobandz.com/"},
    }
    if artist.get("aliases"):
        artist_node["alternateName"] = artist["aliases"]

    graph: list[dict[str, Any]] = [person_node, artist_node]

    for entity in registry["entities"]["entities"]:
        if entity["id"] in {person["id"], artist["id"]}:
            continue
        if entity["type"] in {"Organization", "WebSite", "SoftwareApplication"} and entity["status"] == "active":
            node: dict[str, Any] = {
                "@type": entity["type"],
                "@id": f"https://iambandobandz.com/#{entity['id'].replace(':', '-')}",
                "name": entity["name"],
                "url": entity["canonical_url"],
            }
            if entity["id"] == "domain:iambandobandz-com":
                node["about"] = {"@id": "https://iambandobandz.com/#iambandobandz"}
                node["inLanguage"] = "en-US"
            graph.append(node)

    return {"@context": "https://schema.org", "@graph": graph}


def build_public_manifest(registry: dict[str, Any]) -> dict[str, Any]:
    profile = registry["profile"]
    return {
        "registry_version": profile["registry_version"],
        "canonical_brand": profile.get("canonical_brand", "iambandobandz"),
        "canonical_domain": profile["canonical_domain"],
        "counts": {
            "entities": len(registry["entities"]["entities"]),
            "platforms": len(registry["platforms"]["platforms"]),
            "releases": len(registry["catalog"]["releases"]),
        },
        "sha256": {name: canonical_sha256(value) for name, value in registry.items()},
    }


def build_sitemap(registry: dict[str, Any]) -> str:
    base = registry["profile"]["canonical_domain"].rstrip("/")
    rows = []
    for route in registry["profile"]["routes"]:
        url = base + route["path"]
        rows.append(
            f"  <url><loc>{url}</loc><changefreq>{route['changefreq']}</changefreq><priority>{route['priority']:.1f}</priority></url>"
        )
    return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n" + "\n".join(rows) + "\n</urlset>\n"
