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
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

VERSION = "1.2.0"
SCHEMA_VERSION = "frontier-radar-feed/1.2"
SCORE_MODEL_VERSION = "frontier-radar-score/1.2"
USER_AGENT = f"MassiveMagnetics-FrontierRadar/{VERSION} (+https://iambandobandz.com/frontier-radar/)"
DEFAULT_TIMEOUT = 20
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
MAX_RETRIES = 2
DEFAULT_MIN_ITEMS = 12
DEFAULT_MIN_HEALTHY_SOURCES = 2
ARXIV_MIN_INTERVAL_SECONDS = 3.05

API_HOSTS = {
    "api.github.com",
    "huggingface.co",
    "export.arxiv.org",
}
ITEM_HOSTS = {
    "github": {"github.com"},
    "huggingface": {"huggingface.co"},
    "arxiv": {"arxiv.org", "www.arxiv.org", "export.arxiv.org"},
}

QUERIES = [
    "continual learning",
    "online learning agent",
    "world model agent",
    "test time training",
    "recurrent memory model",
    "state space model",
    "mixture of experts routing",
    "small language model",
    "model compression distillation",
    "local multimodal agent",
    "autonomous agent memory",
    "experience replay learning",
    "audio generation model",
    "singing voice generation",
]

FRONTIER_TERMS = {
    "continual learning": 1.0,
    "online learning": 1.0,
    "world model": 0.95,
    "test time training": 0.95,
    "test-time training": 0.95,
    "self-improving": 0.9,
    "self improving": 0.9,
    "experience replay": 0.8,
    "recurrent memory": 0.8,
    "memory": 0.42,
    "agent": 0.34,
    "autonomous": 0.4,
    "sparse": 0.55,
    "mixture of experts": 0.78,
    "routing": 0.45,
    "compression": 0.55,
    "distillation": 0.52,
    "quantization": 0.48,
    "small language model": 0.72,
    "local": 0.28,
    "offline": 0.38,
    "multimodal": 0.35,
    "audio generation": 0.68,
    "singing voice": 0.68,
    "speech generation": 0.52,
    "recurrent": 0.4,
    "state space": 0.58,
    "reasoning": 0.34,
    "jepa": 0.62,
    "latent action": 0.52,
}

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


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
    matched_queries: tuple[str, ...]
    signal_id: str = ""
    first_seen_at: str | None = None
    seen_count: int = 1
    metric_deltas: dict[str, float] | None = None
    novelty_score: float = 1.0
    velocity_score: float = 0.0
    trend: str = "new"
    score: float = 0.0
    score_breakdown: dict[str, float] | None = None
    evidence_sha256: str = ""
    ranking_sha256: str = ""


class ScanQualityError(RuntimeError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now(now: datetime | None = None) -> str:
    return (now or utc_now()).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


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
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def age_days(timestamp: str | None, now: datetime | None = None) -> float:
    if not timestamp:
        return 365.0
    now = now or utc_now()
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return 365.0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0.0, (now - dt.astimezone(timezone.utc)).total_seconds() / 86400.0)


def clean_text(value: Any, limit: int) -> str:
    text = CONTROL_CHARS.sub("", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def signal_id_for(source: str, external_id: str) -> str:
    return hashlib.sha256(f"{source}\0{external_id}".encode("utf-8")).hexdigest()


def _url_host(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme.lower() != "https":
        raise ValueError("URL must use HTTPS")
    if parsed.username or parsed.password:
        raise ValueError("URL credentials are not permitted")
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise ValueError("URL host missing")
    return host


def require_api_url(url: str) -> str:
    host = _url_host(url)
    if host not in API_HOSTS:
        raise ValueError(f"API host not allowlisted: {host}")
    return url


def normalize_item_url(source: str, url: str) -> str:
    value = clean_text(url, 2048)
    if source == "arxiv" and value.startswith("http://arxiv.org/"):
        value = "https://arxiv.org/" + value[len("http://arxiv.org/"):]
    host = _url_host(value)
    allowed = ITEM_HOSTS.get(source)
    if not allowed or host not in allowed:
        raise ValueError(f"item host not allowlisted for {source}: {host}")
    return value


def normalize_metrics(metrics: dict[str, Any]) -> dict[str, float | int]:
    out: dict[str, float | int] = {}
    for key, raw in sorted(metrics.items()):
        name = clean_text(key, 64)
        if not name:
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(value):
            continue
        value = max(0.0, value)
        if float(value).is_integer() and value <= 9_007_199_254_740_991:
            out[name] = int(value)
        else:
            out[name] = round(value, 6)
    return out


def normalize_item(item: RadarItem) -> RadarItem:
    source = clean_text(item.source, 32).lower()
    external_id = clean_text(item.external_id, 512)
    if source not in ITEM_HOSTS:
        raise ValueError(f"unsupported source: {source}")
    if not external_id:
        raise ValueError("external_id missing")
    title = clean_text(item.title, 280)
    if not title:
        raise ValueError("title missing")
    url = normalize_item_url(source, item.url)
    matched = tuple(sorted({clean_text(q, 120) for q in item.matched_queries if clean_text(q, 120)}))
    if not matched:
        raise ValueError("matched_queries missing")
    sid = item.signal_id or signal_id_for(source, external_id)
    if not HEX64.fullmatch(sid):
        raise ValueError("invalid signal_id")
    return replace(
        item,
        source=source,
        external_id=external_id,
        title=title,
        url=url,
        summary=clean_text(item.summary, 2000),
        author=clean_text(item.author, 300) or "unknown",
        published_at=iso_or_none(item.published_at),
        updated_at=iso_or_none(item.updated_at),
        metrics=normalize_metrics(item.metrics),
        indie_hint=max(0.0, min(1.0, float(item.indie_hint))),
        reproducibility_hint=max(0.0, min(1.0, float(item.reproducibility_hint))),
        matched_queries=matched,
        signal_id=sid,
        seen_count=max(1, int(item.seen_count)),
    )


def observation_payload(item: RadarItem) -> dict[str, Any]:
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
    }


def evidence_hash(item: RadarItem) -> str:
    return sha256_json(observation_payload(item))


def ranking_payload(item: RadarItem) -> dict[str, Any]:
    return {
        "signal_id": item.signal_id,
        "indie_hint": item.indie_hint,
        "reproducibility_hint": item.reproducibility_hint,
        "matched_queries": list(item.matched_queries),
        "novelty_score": item.novelty_score,
        "velocity_score": item.velocity_score,
        "trend": item.trend,
        "score": item.score,
        "score_breakdown": item.score_breakdown,
        "evidence_sha256": item.evidence_sha256,
        "score_model_version": SCORE_MODEL_VERSION,
    }


def ranking_hash(item: RadarItem) -> str:
    return sha256_json(ranking_payload(item))


def text_signal_score(title: str, summary: str) -> float:
    haystack = f"{title} {summary}".lower()
    raw = sum(weight for term, weight in FRONTIER_TERMS.items() if term in haystack)
    return min(1.0, raw / 2.6)


def traction_score(metrics: dict[str, float | int]) -> float:
    stars = float(metrics.get("stars", 0) or 0)
    forks = float(metrics.get("forks", 0) or 0)
    downloads = float(metrics.get("downloads", 0) or 0)
    likes = float(metrics.get("likes", 0) or 0)
    signal = stars + 2.0 * forks + downloads / 250.0 + 0.7 * likes
    return min(1.0, math.log1p(max(0.0, signal)) / math.log1p(5000.0))


def metric_velocity(current: dict[str, float | int], previous: dict[str, Any]) -> tuple[dict[str, float], float]:
    deltas: dict[str, float] = {}
    weighted_gain = 0.0
    weights = {"stars": 1.0, "forks": 2.0, "downloads": 0.004, "likes": 0.7}
    for key, current_value in current.items():
        try:
            before = float(previous.get(key, 0) or 0)
            now_value = float(current_value or 0)
        except (TypeError, ValueError):
            continue
        delta = max(0.0, now_value - before)
        if delta > 0:
            deltas[key] = round(delta, 6)
            weighted_gain += delta * weights.get(key, 0.2)
    velocity = min(1.0, math.log1p(weighted_gain) / math.log1p(1000.0))
    return deltas, velocity


def enrich_history(item: RadarItem, previous: dict[str, Any] | None, generated_at: str) -> RadarItem:
    if not previous:
        return replace(
            item,
            first_seen_at=generated_at,
            seen_count=1,
            metric_deltas={},
            novelty_score=1.0,
            velocity_score=0.0,
            trend="new",
        )
    deltas, velocity = metric_velocity(item.metrics, previous.get("metrics") or {})
    seen_count = max(1, int(previous.get("seen_count") or 1)) + 1
    first_seen = iso_or_none(previous.get("first_seen_at")) or generated_at
    novelty = max(0.05, min(0.55, 1.0 / math.sqrt(seen_count)))
    return replace(
        item,
        first_seen_at=first_seen,
        seen_count=seen_count,
        metric_deltas=deltas,
        novelty_score=round(novelty, 4),
        velocity_score=round(velocity, 4),
        trend="stable",
    )


def score_item(item: RadarItem, now: datetime | None = None) -> RadarItem:
    item = normalize_item(item)
    now = now or utc_now()
    reference_time = item.updated_at or item.published_at
    recency = math.exp(-age_days(reference_time, now) / 21.0)
    frontier = text_signal_score(item.title, item.summary)
    traction = traction_score(item.metrics)
    indie = item.indie_hint
    reproducible = item.reproducibility_hint
    novelty = max(0.0, min(1.0, item.novelty_score))
    velocity = max(0.0, min(1.0, item.velocity_score))

    breakdown = {
        "frontier": round(frontier, 4),
        "recency": round(recency, 4),
        "traction": round(traction, 4),
        "indie": round(indie, 4),
        "reproducibility": round(reproducible, 4),
        "novelty": round(novelty, 4),
        "velocity": round(velocity, 4),
    }
    total = (
        0.28 * frontier
        + 0.16 * recency
        + 0.12 * traction
        + 0.14 * indie
        + 0.14 * reproducible
        + 0.08 * novelty
        + 0.08 * velocity
    )
    score = round(total * 100.0, 2)
    trend = "stable"
    if frontier >= 0.70 and score >= 78 and (velocity >= 0.35 or novelty >= 0.90):
        trend = "breakout"
    elif score >= 65 and velocity >= 0.12:
        trend = "rising"
    elif novelty >= 0.90:
        trend = "new"

    scored = replace(item, score=score, score_breakdown=breakdown, trend=trend)
    evidence = evidence_hash(scored)
    scored = replace(scored, evidence_sha256=evidence)
    return replace(scored, ranking_sha256=ranking_hash(scored))


class AllowlistedRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        require_api_url(newurl)
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is None:
            return None
        old_host = (urllib.parse.urlsplit(req.full_url).hostname or "").lower()
        new_host = (urllib.parse.urlsplit(newurl).hostname or "").lower()
        if old_host != new_host:
            redirected.remove_header("Authorization")
        return redirected


HTTP_OPENER = urllib.request.build_opener(AllowlistedRedirectHandler())


def _retry_delay(exc: urllib.error.HTTPError, attempt: int) -> float:
    retry_after = exc.headers.get("Retry-After") if exc.headers else None
    if retry_after:
        try:
            return min(30.0, max(0.0, float(retry_after)))
        except ValueError:
            pass
    return min(8.0, 1.0 * (2 ** attempt))


def request_bytes(url: str, *, accept: str, token: str | None = None) -> bytes:
    require_api_url(url)
    headers = {"User-Agent": USER_AGENT, "Accept": accept}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    request = urllib.request.Request(url, headers=headers, method="GET")

    for attempt in range(MAX_RETRIES + 1):
        try:
            with HTTP_OPENER.open(request, timeout=DEFAULT_TIMEOUT) as response:
                require_api_url(response.geturl())
                data = response.read(MAX_RESPONSE_BYTES + 1)
                if len(data) > MAX_RESPONSE_BYTES:
                    raise ValueError("upstream response exceeds size limit")
                return data
        except urllib.error.HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt >= MAX_RETRIES:
                raise
            time.sleep(_retry_delay(exc, attempt))
        except (urllib.error.URLError, TimeoutError):
            if attempt >= MAX_RETRIES:
                raise
            time.sleep(min(8.0, 1.0 * (2 ** attempt)))
    raise RuntimeError("unreachable retry state")


def request_json(url: str, token: str | None = None) -> Any:
    raw = request_bytes(url, accept="application/json", token=token)
    return json.loads(raw.decode("utf-8"))


def request_text(url: str) -> str:
    raw = request_bytes(url, accept="application/atom+xml,text/xml")
    return raw.decode("utf-8")


def github_items(query: str, token: str | None) -> list[RadarItem]:
    cutoff = (utc_now() - timedelta(days=180)).date().isoformat()
    q = f'{query} in:name,description,readme pushed:>{cutoff}'
    params = urllib.parse.urlencode({"q": q, "sort": "updated", "order": "desc", "per_page": 15})
    payload = request_json(f"https://api.github.com/search/repositories?{params}", token=token)
    items: list[RadarItem] = []
    for repo in payload.get("items", []):
        owner = repo.get("owner") or {}
        description = repo.get("description") or ""
        license_info = repo.get("license") or {}
        has_license = bool(license_info.get("spdx_id") and license_info.get("spdx_id") != "NOASSERTION")
        owner_type = str(owner.get("type") or "")
        archived = bool(repo.get("archived"))
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
                metrics={
                    "stars": int(repo.get("stargazers_count") or 0),
                    "forks": int(repo.get("forks_count") or 0),
                },
                indie_hint=1.0 if owner_type == "User" else 0.35,
                reproducibility_hint=(0.95 if has_license else 0.68) * (0.55 if archived else 1.0),
                matched_queries=(query,),
            )
        )
    return items


def huggingface_items(query: str) -> list[RadarItem]:
    params = urllib.parse.urlencode(
        {"search": query, "sort": "lastModified", "direction": "-1", "limit": 15}
    )
    payload = request_json(f"https://huggingface.co/api/models?{params}")
    if not isinstance(payload, list):
        raise ValueError("unexpected Hugging Face payload")
    items: list[RadarItem] = []
    for model in payload:
        model_id = str(model.get("id") or model.get("modelId") or "")
        if not model_id:
            continue
        tags = model.get("tags") or []
        pipeline = str(model.get("pipeline_tag") or "")
        summary = " ".join([pipeline, *(str(tag) for tag in tags[:20])]).strip()
        author = model_id.split("/", 1)[0] if "/" in model_id else "unknown"
        has_runtime_metadata = bool(model.get("library_name") or model.get("config") or model.get("pipeline_tag"))
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
                metrics={
                    "downloads": int(model.get("downloads") or 0),
                    "likes": int(model.get("likes") or 0),
                },
                indie_hint=0.65,
                reproducibility_hint=0.86 if has_runtime_metadata else 0.66,
                matched_queries=(query,),
            )
        )
    return items


def _entry_text(entry: ET.Element, tag: str, ns: dict[str, str]) -> str:
    node = entry.find(tag, ns)
    return (node.text or "").strip() if node is not None and node.text else ""


def arxiv_items(query: str) -> list[RadarItem]:
    search = f'all:"{query}"'
    params = urllib.parse.urlencode(
        {
            "search_query": search,
            "start": 0,
            "max_results": 15,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    xml = request_text(f"https://export.arxiv.org/api/query?{params}")
    root = ET.fromstring(xml)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items: list[RadarItem] = []
    for entry in root.findall("atom:entry", ns):
        url = _entry_text(entry, "atom:id", ns).replace("http://arxiv.org/", "https://arxiv.org/")
        title = _entry_text(entry, "atom:title", ns)
        summary = _entry_text(entry, "atom:summary", ns)
        authors = [
            _entry_text(author, "atom:name", ns)
            for author in entry.findall("atom:author", ns)
        ]
        external_id = url.rsplit("/", 1)[-1] if url else title
        items.append(
            RadarItem(
                source="arxiv",
                external_id=external_id,
                title=title,
                url=url,
                summary=summary,
                author=", ".join(a for a in authors if a) or "unknown",
                published_at=iso_or_none(_entry_text(entry, "atom:published", ns)),
                updated_at=iso_or_none(_entry_text(entry, "atom:updated", ns)),
                metrics={},
                indie_hint=0.45,
                reproducibility_hint=0.56,
                matched_queries=(query,),
            )
        )
    return items


def dedupe(
    items: Iterable[RadarItem],
    validation_errors: list[dict[str, str]] | None = None,
) -> list[RadarItem]:
    best: dict[str, RadarItem] = {}
    for raw in items:
        try:
            item = normalize_item(raw)
        except (TypeError, ValueError, OverflowError) as exc:
            if validation_errors is not None:
                validation_errors.append(
                    {
                        "source": clean_text(getattr(raw, "source", "unknown"), 32),
                        "query": "normalization",
                        "error": f"{type(exc).__name__}: {exc}"[:500],
                    }
                )
            continue
        current = best.get(item.signal_id)
        if current is None:
            best[item.signal_id] = item
            continue
        merged_queries = tuple(sorted(set(current.matched_queries) | set(item.matched_queries)))
        winner = item if item.score > current.score else current
        best[item.signal_id] = replace(winner, matched_queries=merged_queries)
    return list(best.values())


def _new_health() -> dict[str, dict[str, Any]]:
    return {
        name: {
            "requests": 0,
            "successes": 0,
            "failures": 0,
            "items": 0,
            "duration_ms": 0,
            "healthy": False,
            "last_error": None,
        }
        for name in ("github", "huggingface", "arxiv")
    }


def safe_collect(
    source: str,
    query: str,
    fn: Callable[[], list[RadarItem]],
    health: dict[str, dict[str, Any]],
    errors: list[dict[str, str]],
) -> list[RadarItem]:
    started = time.monotonic()
    health[source]["requests"] += 1
    try:
        items = fn()
        health[source]["successes"] += 1
        health[source]["items"] += len(items)
        return items
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        ET.ParseError,
        ValueError,
        TypeError,
        OverflowError,
        json.JSONDecodeError,
    ) as exc:
        health[source]["failures"] += 1
        message = f"{type(exc).__name__}: {exc}"[:500]
        health[source]["last_error"] = message
        errors.append({"source": source, "query": clean_text(query, 120), "error": message})
        return []
    finally:
        health[source]["duration_ms"] += int((time.monotonic() - started) * 1000)


def load_previous_feed(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def previous_index(previous_feed: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not previous_feed:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for item in previous_feed.get("items") or []:
        if not isinstance(item, dict):
            continue
        sid = item.get("signal_id")
        if not sid and item.get("source") and item.get("external_id"):
            sid = signal_id_for(str(item["source"]), str(item["external_id"]))
        if isinstance(sid, str) and HEX64.fullmatch(sid):
            out[sid] = item
    return out


def build_feed(
    previous_feed: dict[str, Any] | None = None,
    max_items: int = 160,
    *,
    pause_seconds: float = ARXIV_MIN_INTERVAL_SECONDS,
) -> dict[str, Any]:
    started = time.monotonic()
    token = os.environ.get("GITHUB_TOKEN")
    errors: list[dict[str, str]] = []
    health = _new_health()
    collected: list[RadarItem] = []
    generated_at = iso_now()

    for query in QUERIES:
        collected.extend(
            safe_collect("github", query, lambda q=query: github_items(q, token), health, errors)
        )
        collected.extend(
            safe_collect("huggingface", query, lambda q=query: huggingface_items(q), health, errors)
        )
        collected.extend(
            safe_collect("arxiv", query, lambda q=query: arxiv_items(q), health, errors)
        )
        if pause_seconds:
            time.sleep(pause_seconds)

    for value in health.values():
        required_successes = max(1, math.ceil(value["requests"] * 0.5))
        value["success_ratio"] = round(
            value["successes"] / max(1, value["requests"]), 4
        )
        value["healthy"] = (
            value["successes"] >= required_successes and value["items"] > 0
        )

    prev = previous_index(previous_feed)
    normalized = dedupe(collected, errors)
    enriched: list[RadarItem] = []
    for item in normalized:
        historical = enrich_history(item, prev.get(item.signal_id), generated_at)
        enriched.append(score_item(historical))

    enriched.sort(
        key=lambda item: (
            item.trend == "breakout",
            item.trend == "rising",
            item.score,
            item.velocity_score,
            item.updated_at or item.published_at or "",
        ),
        reverse=True,
    )
    enriched = enriched[:max_items]

    healthy_sources = sum(1 for value in health.values() if value["healthy"])
    previous_hash = None
    if previous_feed and isinstance(previous_feed.get("feed_sha256"), str):
        candidate = previous_feed["feed_sha256"]
        if HEX64.fullmatch(candidate):
            previous_hash = candidate

    feed: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "score_model_version": SCORE_MODEL_VERSION,
        "generated_at": generated_at,
        "query_count": len(QUERIES),
        "queries": list(QUERIES),
        "source_count": len(health),
        "healthy_source_count": healthy_sources,
        "item_count": len(enriched),
        "breakout_count": sum(1 for item in enriched if item.trend == "breakout"),
        "rising_count": sum(1 for item in enriched if item.trend == "rising"),
        "errors": errors[:100],
        "source_health": health,
        "scan_duration_ms": int((time.monotonic() - started) * 1000),
        "previous_snapshot_sha256": previous_hash,
        "items": [asdict(item) for item in enriched],
    }
    feed["content_sha256"] = sha256_json(
        {
            "schema_version": feed["schema_version"],
            "score_model_version": feed["score_model_version"],
            "queries": feed["queries"],
            "items": feed["items"],
        }
    )
    feed["feed_sha256"] = sha256_json(feed)
    return feed


def verify_feed_hash(feed: dict[str, Any]) -> bool:
    expected = feed.get("feed_sha256")
    if not isinstance(expected, str) or not HEX64.fullmatch(expected):
        return False
    payload = dict(feed)
    payload.pop("feed_sha256", None)
    return sha256_json(payload) == expected


def validate_feed(
    feed: dict[str, Any],
    *,
    min_items: int = DEFAULT_MIN_ITEMS,
    min_healthy_sources: int = DEFAULT_MIN_HEALTHY_SOURCES,
) -> list[str]:
    issues: list[str] = []
    if feed.get("schema_version") != SCHEMA_VERSION:
        issues.append(f"schema_version must be {SCHEMA_VERSION}")
    if feed.get("score_model_version") != SCORE_MODEL_VERSION:
        issues.append(f"score_model_version must be {SCORE_MODEL_VERSION}")
    if not verify_feed_hash(feed):
        issues.append("feed_sha256 verification failed")

    content_expected = feed.get("content_sha256")
    content_actual = sha256_json(
        {
            "schema_version": feed.get("schema_version"),
            "score_model_version": feed.get("score_model_version"),
            "queries": feed.get("queries"),
            "items": feed.get("items"),
        }
    )
    if content_expected != content_actual:
        issues.append("content_sha256 verification failed")

    items = feed.get("items")
    if not isinstance(items, list):
        return issues + ["items must be a list"]
    if feed.get("item_count") != len(items):
        issues.append("item_count does not match items length")
    if len(items) < min_items:
        issues.append(f"item_count below quality floor ({len(items)} < {min_items})")

    healthy_sources = int(feed.get("healthy_source_count") or 0)
    if healthy_sources < min_healthy_sources:
        issues.append(
            f"healthy_source_count below quality floor ({healthy_sources} < {min_healthy_sources})"
        )

    ids: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            issues.append(f"items[{index}] is not an object")
            continue
        sid = item.get("signal_id")
        if not isinstance(sid, str) or not HEX64.fullmatch(sid):
            issues.append(f"items[{index}].signal_id invalid")
        elif sid in ids:
            issues.append(f"duplicate signal_id at items[{index}]")
        else:
            ids.add(sid)
        source = str(item.get("source") or "")
        try:
            normalize_item_url(source, str(item.get("url") or ""))
        except ValueError as exc:
            issues.append(f"items[{index}].url invalid: {exc}")
        try:
            score = float(item.get("score"))
        except (TypeError, ValueError):
            issues.append(f"items[{index}].score invalid")
        else:
            if not 0.0 <= score <= 100.0:
                issues.append(f"items[{index}].score out of bounds")
        evidence = item.get("evidence_sha256")
        ranking = item.get("ranking_sha256")
        if not isinstance(evidence, str) or not HEX64.fullmatch(evidence):
            issues.append(f"items[{index}].evidence_sha256 invalid")
        if not isinstance(ranking, str) or not HEX64.fullmatch(ranking):
            issues.append(f"items[{index}].ranking_sha256 invalid")
        try:
            reconstructed = RadarItem(
                **{
                    **item,
                    "matched_queries": tuple(item.get("matched_queries") or ()),
                }
            )
        except (TypeError, ValueError):
            issues.append(f"items[{index}] cannot be reconstructed")
        else:
            if isinstance(evidence, str) and evidence_hash(reconstructed) != evidence:
                issues.append(f"items[{index}].evidence_sha256 verification failed")
            if isinstance(ranking, str) and ranking_hash(reconstructed) != ranking:
                issues.append(f"items[{index}].ranking_sha256 verification failed")
    return issues


def build_status(
    feed: dict[str, Any] | None,
    *,
    healthy: bool,
    issues: list[str],
    preserved_previous: bool,
    file_sha256: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "frontier-radar-status/1.2",
        "generated_at": (feed or {}).get("generated_at") or iso_now(),
        "item_count": int((feed or {}).get("item_count") or 0),
        "healthy_source_count": int((feed or {}).get("healthy_source_count") or 0),
        "error_count": len((feed or {}).get("errors") or []),
        "feed_sha256": (feed or {}).get("feed_sha256"),
        "content_sha256": (feed or {}).get("content_sha256"),
        "file_sha256": file_sha256,
        "healthy": healthy,
        "preserved_previous": preserved_previous,
        "issues": issues[:25],
        "version": VERSION,
    }


def write_feed(
    output: Path,
    status_output: Path | None = None,
    *,
    min_items: int = DEFAULT_MIN_ITEMS,
    min_healthy_sources: int = DEFAULT_MIN_HEALTHY_SOURCES,
) -> dict[str, Any]:
    previous_feed = load_previous_feed(output)
    feed = build_feed(previous_feed=previous_feed)
    issues = validate_feed(
        feed,
        min_items=min_items,
        min_healthy_sources=min_healthy_sources,
    )
    status_output = status_output or output.with_name("status.json")
    status_output.parent.mkdir(parents=True, exist_ok=True)

    digest_output = output.with_name("feed.sha256")
    if issues:
        status = build_status(
            feed,
            healthy=False,
            issues=issues,
            preserved_previous=output.exists(),
        )
        status_output.write_text(
            json.dumps(status, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        raise ScanQualityError("; ".join(issues))

    output.parent.mkdir(parents=True, exist_ok=True)
    feed_text = json.dumps(feed, indent=2, ensure_ascii=False) + "\n"
    file_sha256 = hashlib.sha256(feed_text.encode("utf-8")).hexdigest()
    output.write_text(feed_text, encoding="utf-8")
    digest_output.write_text(f"{file_sha256}  {output.name}\n", encoding="ascii")
    status = build_status(
        feed,
        healthy=True,
        issues=[],
        preserved_previous=False,
        file_sha256=file_sha256,
    )
    status_output.write_text(
        json.dumps(status, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return feed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan public AI frontier signals and build a verified, last-known-good static feed."
    )
    parser.add_argument("--output", type=Path, default=Path("frontier-radar/data/feed.json"))
    parser.add_argument("--status-output", type=Path, default=None)
    parser.add_argument("--min-items", type=int, default=DEFAULT_MIN_ITEMS)
    parser.add_argument("--min-healthy-sources", type=int, default=DEFAULT_MIN_HEALTHY_SOURCES)
    args = parser.parse_args()
    try:
        feed = write_feed(
            args.output,
            args.status_output,
            min_items=max(1, args.min_items),
            min_healthy_sources=max(1, args.min_healthy_sources),
        )
    except ScanQualityError as exc:
        print(json.dumps({"ok": False, "version": VERSION, "error": str(exc)}))
        return 2
    print(
        json.dumps(
            {
                "ok": True,
                "version": VERSION,
                "item_count": feed["item_count"],
                "healthy_sources": feed["healthy_source_count"],
                "breakouts": feed["breakout_count"],
                "feed_sha256": feed["feed_sha256"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
