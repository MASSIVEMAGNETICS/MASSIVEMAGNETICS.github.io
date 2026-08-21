from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

try:
    from tools.frontier_radar import validate_feed
except ModuleNotFoundError:
    from frontier_radar import validate_feed


def age_hours(value: str | None) -> float:
    if not value:
        return float("inf")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return float("inf")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(
        0.0,
        (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 3600.0,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Frontier Radar V1.2 feed integrity.")
    parser.add_argument("feed", type=Path)
    parser.add_argument("--status", type=Path, default=None)
    parser.add_argument("--digest", type=Path, default=None)
    parser.add_argument("--min-items", type=int, default=12)
    parser.add_argument("--min-healthy-sources", type=int, default=2)
    parser.add_argument("--max-age-hours", type=float, default=None)
    args = parser.parse_args()

    feed_bytes = args.feed.read_bytes()
    payload = json.loads(feed_bytes.decode("utf-8"))
    issues = validate_feed(
        payload,
        min_items=max(1, args.min_items),
        min_healthy_sources=max(1, args.min_healthy_sources),
    )
    if args.max_age_hours is not None and age_hours(payload.get("generated_at")) > args.max_age_hours:
        issues.append("feed is older than the configured maximum age")

    digest_path = args.digest
    if digest_path is None:
        candidate = args.feed.with_name("feed.sha256")
        if candidate.exists():
            digest_path = candidate
    actual_file_sha256 = hashlib.sha256(feed_bytes).hexdigest()
    if digest_path:
        expected_file_sha256 = digest_path.read_text(encoding="ascii").strip().split()[0]
        if expected_file_sha256 != actual_file_sha256:
            issues.append("feed file SHA-256 mismatch")

    if args.status:
        status = json.loads(args.status.read_text(encoding="utf-8"))
        if status.get("feed_sha256") != payload.get("feed_sha256"):
            issues.append("status/feed hash mismatch")
        if status.get("file_sha256") and status.get("file_sha256") != actual_file_sha256:
            issues.append("status/file hash mismatch")
        if status.get("healthy") is not True:
            issues.append("status is not healthy")

    if issues:
        for issue in issues:
            print(f"ERROR: {issue}")
        return 2

    print(
        json.dumps(
            {
                "ok": True,
                "feed_sha256": payload["feed_sha256"],
                "items": payload["item_count"],
                "healthy_sources": payload["healthy_source_count"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
