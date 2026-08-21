from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

USER_AGENT = "MassiveMagnetics-FrontierRadar/0.1 (+https://iambandobandz.com/frontier-radar/)"
DEFAULT_TIMEOUT = 20

QUERIES = [
    "continual learning",
    "online learning agent",
    "world model agent",
    "small language model",
    "mixture of experts routing",
    "memory agent",
    "local autonomous agent",
    "neural compression",
    "audio generation model",
    "singing voice generation",
]

FRONTIER_TERMS = {
    "continual learning": 1.0,
    "online learning": 1.0,
    "world model": 0.9,
    "self-improving": 0.9,
    "self improving": 0.9,
    "memory": 0.45,
    "agent": 0.35,
    "sparse": 0.55,
    "mixture of experts": 0.75,
    "routing": 0.45,
    "compression": 0.55,
    "quantization": 0.45,
    "small language model": 0.7,
    "local": 0.3,
    "offline": 0.4,
    "audio generation": 0.65,
    "singing voice": 0.65,
    "speech generation": 0.5,
    "recurrent": 0.45,
    "state space": 0.55,
    "reasoning": 0.35,
}


@dataclass(frozen=True)
class RadarItem:
    source: str
    external_id: str
    title: str
    url: str
    summary: str
    author: str
    published_at: str | None
    updated_at: str | None
    metrics: dict[str, float | int]
    indie_hint: float
    reproducibility_hint: float
    query: str
    score: float = 0.0
    score_breakdown: dict[str, float] | None = None
    evidence_sha256: str = ""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_or_none(value: Any) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return str(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def age_days(timestamp: str | None, now: datetime | None = None) -> float:
    if not timestamp:
        return 30.0
    now = now or utc_now()
    text = timestamp.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return 30.0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0.0, (now - dt.astimezone(timezone.utc)).total_seconds() / 86400.0)


def canonical_payload(item: RadarItem) -> dict[str, Any]:
    return {
        "source": item.source,
        "external_id": item.external_id,
        "title": item.title,
        "url": item.url,
        "summary": item.summary,
        "author": item.author,
        "published_at": item.published_at,
        "updated_at": item.updated_at,
        "metrics": item.metrics,
        "indie_hint": item.indie_hint,
        "reproducibility_hint": item.reproducibility_hint,
        "query": item.query,
    }


def evidence_hash(item: RadarItem) -> str:
    payload = json.dumps(canonical_payload(item), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def text_signal_score(title: str, summary: str) -> float:
    haystack = f"{title} {summary}".lower()
    raw = sum(weight for term, weight in FRONTIER_TERMS.items() if term in haystack)
    return min(1.0, raw / 2.4)


def traction_score(metrics: dict[str, float | int]) -> float:
    stars = float(metrics.get("stars", 0) or 0)
    forks = float(metrics.get("forks", 0) or 0)
    downloads = float(metrics.get("downloads", 0) or 0)
    citations = float(metrics.get("citations", 0) or 0)
    signal = stars + 2.0 * forks + downloads / 250.0 + 5.0 * citations
    return min(1.0, math.log1p(signal) / math.log1p(5000.0))


def score_item(item: RadarItem, now: datetime | None = None) -> RadarItem:
    now = now or utc_now()
    reference_time = item.updated_at or item.published_at
    recency = math.exp(-age_days(reference_time, now) / 21.0)
    frontier = text_signal_score(item.title, item.summary)
    traction = traction_score(item.metrics)
    indie = max(0.0, min(1.0, float(item.indie_hint)))
    reproducible = max(0.0, min(1.0, float(item.reproducibility_hint)))

    breakdown = {
        "frontier": round(frontier, 4),
        "recency": round(recency, 4),
        "traction": round(traction, 4),
        "indie": round(indie, 4),
        "reproducibility": round(reproducible, 4),
    }
    total = (
        0.34 * frontier
        + 0.22 * recency
        + 0.14 * traction
        + 0.14 * indie
        + 0.16 * reproducible
    )
    scored = RadarItem(**{**asdict(item), "score": round(total * 100.0, 2), "score_breakdown": breakdown})
    return RadarItem(**{**asdict(scored), "evidence_sha256": evidence_hash(scored)})


def request_json(url: str, token: str | None = None) -> Any:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def request_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/atom+xml,text/xml"})
    with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
        return response.read().decode("utf-8")


def github_items(query: str, token: str | None) -> list[RadarItem]:
    q = f'{query} in:name,description,readme pushed:>2026-01-01'
    params = urllib.parse.urlencode({"q": q, "sort": "updated", "order": "desc", "per_page": 12})
    payload = request_json(f"https://api.github.com/search/repositories?{params}", token=token)
    items: list[RadarItem] = []
    for repo in payload.get("items", []):
        owner = repo.get("owner") or {}
        description = repo.get("description") or ""
        license_info = repo.get("license") or {}
        has_license = bool(license_info.get("spdx_id"))
        owner_type = str(owner.get("type") or "")
        items.append(
            RadarItem(
                source="github",
                external_id=str(repo.get("id") or repo.get("full_name") or ""),
                title=str(repo.get("full_name") or repo.get("name") or "Untitled repository"),
                url=str(repo.get("html_url") or ""),
                summary=description,
                author=str(owner.get("login") or "unknown"),
                published_at=iso_or_none(repo.get("created_at")),
                updated_at=iso_or_none(repo.get("pushed_at") or repo.get("updated_at")),
                metrics={"stars": int(repo.get("stargazers_count") or 0), "forks": int(repo.get("forks_count") or 0)},
                indie_hint=1.0 if owner_type == "User" else 0.35,
                reproducibility_hint=0.95 if has_license else 0.72,
                query=query,
            )
        )
    return items


def huggingface_items(query: str) -> list[RadarItem]:
    params = urllib.parse.urlencode({"search": query, "sort": "lastModified", "direction": "-1", "limit": 12, "full": "true"})
    payload = request_json(f"https://huggingface.co/api/models?{params}")
    items: list[RadarItem] = []
    if not isinstance(payload, list):
        return items
    for model in payload:
        model_id = str(model.get("id") or model.get("modelId") or "")
        if not model_id:
            continue
        tags = model.get("tags") or []
        pipeline = str(model.get("pipeline_tag") or "")
        summary = " ".join([pipeline, *(str(tag) for tag in tags[:16])]).strip()
        author = model_id.split("/", 1)[0] if "/" in model_id else "unknown"
        items.append(
            RadarItem(
                source="huggingface",
                external_id=model_id,
                title=model_id,
                url=f"https://huggingface.co/{model_id}",
                summary=summary,
                author=author,
                published_at=iso_or_none(model.get("createdAt")),
                updated_at=iso_or_none(model.get("lastModified")),
                metrics={"downloads": int(model.get("downloads") or 0), "likes": int(model.get("likes") or 0)},
                indie_hint=0.65,
                reproducibility_hint=0.85 if model.get("library_name") or model.get("config") else 0.68,
                query=query,
            )
        )
    return items


def _entry_text(entry: ET.Element, tag: str, ns: dict[str, str]) -> str:
    node = entry.find(tag, ns)
    return (node.text or "").strip() if node is not None and node.text else ""


def arxiv_items(query: str) -> list[RadarItem]:
    search = f'all:"{query}"'
    params = urllib.parse.urlencode({"search_query": search, "start": 0, "max_results": 12, "sortBy": "submittedDate", "sortOrder": "descending"})
    xml = request_text(f"https://export.arxiv.org/api/query?{params}")
    root = ET.fromstring(xml)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items: list[RadarItem] = []
    for entry in root.findall("atom:entry", ns):
        url = _entry_text(entry, "atom:id", ns)
        title = re.sub(r"\s+", " ", _entry_text(entry, "atom:title", ns))
        summary = re.sub(r"\s+", " ", _entry_text(entry, "atom:summary", ns))
        published = _entry_text(entry, "atom:published", ns)
        updated = _entry_text(entry, "atom:updated", ns)
        authors = [re.sub(r"\s+", " ", _entry_text(author, "atom:name", ns)) for author in entry.findall("atom:author", ns)]
        external_id = url.rsplit("/", 1)[-1] if url else title
        items.append(
            RadarItem(
                source="arxiv",
                external_id=external_id,
                title=title,
                url=url,
                summary=summary[:1200],
                author=", ".join(a for a in authors if a)[:300] or "unknown",
                published_at=iso_or_none(published),
                updated_at=iso_or_none(updated),
                metrics={},
                indie_hint=0.45,
                reproducibility_hint=0.56,
                query=query,
            )
        )
    return items


def dedupe(items: Iterable[RadarItem]) -> list[RadarItem]:
    best: dict[tuple[str, str], RadarItem] = {}
    for item in items:
        key = (item.source, item.external_id or item.url)
        current = best.get(key)
        if current is None or item.score > current.score:
            best[key] = item
    return list(best.values())


def safe_collect(name: str, fn, errors: list[dict[str, str]]) -> list[RadarItem]:
    try:
        return fn()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ET.ParseError, ValueError, json.JSONDecodeError) as exc:
        errors.append({"source": name, "error": f"{type(exc).__name__}: {exc}"[:500]})
        return []


def build_feed(max_items: int = 120) -> dict[str, Any]:
    token = os.environ.get("GITHUB_TOKEN")
    errors: list[dict[str, str]] = []
    collected: list[RadarItem] = []

    for query in QUERIES:
        collected.extend(safe_collect(f"github:{query}", lambda q=query: github_items(q, token), errors))
        collected.extend(safe_collect(f"huggingface:{query}", lambda q=query: huggingface_items(q), errors))
        collected.extend(safe_collect(f"arxiv:{query}", lambda q=query: arxiv_items(q), errors))
        time.sleep(0.15)

    scored = dedupe(score_item(item) for item in collected if item.url and item.title)
    scored.sort(key=lambda item: (item.score, item.updated_at or item.published_at or ""), reverse=True)
    scored = scored[:max_items]
    now = utc_now().isoformat().replace("+00:00", "Z")

    feed = {
        "schema_version": "frontier-radar-feed/0.1",
        "generated_at": now,
        "query_count": len(QUERIES),
        "source_count": 3,
        "item_count": len(scored),
        "errors": errors,
        "items": [asdict(item) for item in scored],
    }
    feed_bytes = json.dumps(feed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    feed["feed_sha256"] = hashlib.sha256(feed_bytes).hexdigest()
    return feed


def write_feed(output: Path, status_output: Path | None = None) -> dict[str, Any]:
    feed = build_feed()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(feed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    status_output = status_output or output.with_name("status.json")
    status = {
        "generated_at": feed["generated_at"],
        "item_count": feed["item_count"],
        "error_count": len(feed["errors"]),
        "feed_sha256": feed["feed_sha256"],
        "healthy": feed["item_count"] > 0,
    }
    status_output.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    return feed


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan public AI frontier signals and build a verifiable static feed.")
    parser.add_argument("--output", type=Path, default=Path("frontier-radar/data/feed.json"))
    parser.add_argument("--status-output", type=Path, default=None)
    args = parser.parse_args()
    feed = write_feed(args.output, args.status_output)
    print(json.dumps({"item_count": feed["item_count"], "errors": len(feed["errors"]), "feed_sha256": feed["feed_sha256"]}))
    return 0 if feed["item_count"] > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
