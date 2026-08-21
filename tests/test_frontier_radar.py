from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from tools.frontier_radar import (
    RadarItem,
    ScanQualityError,
    dedupe,
    enrich_history,
    evidence_hash,
    normalize_item_url,
    ranking_hash,
    score_item,
    sha256_json,
    signal_id_for,
    text_signal_score,
    traction_score,
    validate_feed,
    verify_feed_hash,
    write_feed,
)


class FrontierRadarV12Tests(unittest.TestCase):
    def item(self, **overrides):
        base = dict(
            source="github",
            external_id="1",
            title="tiny continual learning world model",
            url="https://github.com/example/repo",
            summary="offline sparse agent with recurrent memory and compression",
            author="indie",
            published_at="2026-08-20T00:00:00Z",
            updated_at="2026-08-20T00:00:00Z",
            metrics={"stars": 100, "forks": 10},
            indie_hint=1.0,
            reproducibility_hint=0.95,
            matched_queries=("continual learning",),
        )
        base.update(overrides)
        return RadarItem(**base)

    def scored(self, **overrides):
        now = datetime(2026, 8, 21, tzinfo=timezone.utc)
        return score_item(self.item(**overrides), now=now)

    def test_frontier_terms_raise_signal(self):
        self.assertGreater(text_signal_score("continual learning world model", "recurrent memory"), 0.5)
        self.assertEqual(text_signal_score("cooking notes", "banana bread"), 0.0)

    def test_traction_is_bounded(self):
        self.assertGreaterEqual(traction_score({"stars": 999999}), 0.0)
        self.assertLessEqual(traction_score({"stars": 999999}), 1.0)

    def test_scoring_hashes_and_signal_identity(self):
        scored = self.scored()
        self.assertGreater(scored.score, 50)
        self.assertLessEqual(scored.score, 100)
        self.assertEqual(scored.signal_id, signal_id_for("github", "1"))
        self.assertEqual(scored.evidence_sha256, evidence_hash(scored))
        self.assertEqual(scored.ranking_sha256, ranking_hash(scored))

    def test_dedupe_merges_discovery_queries(self):
        a = self.scored(matched_queries=("continual learning",))
        b = self.scored(matched_queries=("world model agent",))
        result = dedupe([a, b])
        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0].matched_queries,
            ("continual learning", "world model agent"),
        )

    def test_history_computes_velocity_and_seen_count(self):
        item = self.item(metrics={"stars": 150, "forks": 20})
        previous = {
            "metrics": {"stars": 100, "forks": 10},
            "seen_count": 3,
            "first_seen_at": "2026-08-01T00:00:00Z",
        }
        enriched = enrich_history(item, previous, "2026-08-21T00:00:00Z")
        self.assertEqual(enriched.seen_count, 4)
        self.assertEqual(enriched.metric_deltas["stars"], 50.0)
        self.assertGreater(enriched.velocity_score, 0)

    def test_dedupe_skips_invalid_upstream_item_without_crashing_scan(self):
        errors = []
        bad = self.item(url="https://evil.example/repo")
        good = self.item(external_id="2", url="https://github.com/example/repo2")
        result = dedupe([bad, good], errors)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].external_id, "2")
        self.assertTrue(errors)

    def test_external_url_allowlist_blocks_javascript_and_wrong_host(self):
        with self.assertRaises(ValueError):
            normalize_item_url("github", "javascript:alert(1)")
        with self.assertRaises(ValueError):
            normalize_item_url("github", "https://evil.example/repo")
        self.assertEqual(
            normalize_item_url("arxiv", "http://arxiv.org/abs/1234.5678"),
            "https://arxiv.org/abs/1234.5678",
        )

    def valid_feed(self):
        items = [self.scored(external_id=str(i), url=f"https://github.com/example/repo{i}") for i in range(12)]
        feed = {
            "schema_version": "frontier-radar-feed/1.2",
            "score_model_version": "frontier-radar-score/1.2",
            "generated_at": "2026-08-21T00:00:00Z",
            "query_count": 14,
            "queries": ["continual learning"],
            "source_count": 3,
            "healthy_source_count": 3,
            "item_count": len(items),
            "breakout_count": 0,
            "rising_count": 0,
            "errors": [],
            "source_health": {},
            "previous_snapshot_sha256": None,
            "items": [__import__("dataclasses").asdict(item) for item in items],
        }
        feed["content_sha256"] = sha256_json({
            "schema_version": feed["schema_version"],
            "score_model_version": feed["score_model_version"],
            "queries": feed["queries"],
            "items": feed["items"],
        })
        feed["feed_sha256"] = sha256_json(feed)
        return feed

    def test_feed_hash_detects_tampering(self):
        feed = self.valid_feed()
        self.assertTrue(verify_feed_hash(feed))
        feed["items"][0]["title"] = "tampered"
        self.assertFalse(verify_feed_hash(feed))

    def test_validator_rejects_duplicate_signal_ids(self):
        feed = self.valid_feed()
        feed["items"][1]["signal_id"] = feed["items"][0]["signal_id"]
        payload = dict(feed)
        payload.pop("feed_sha256")
        feed["feed_sha256"] = sha256_json(payload)
        issues = validate_feed(feed)
        self.assertTrue(any("duplicate signal_id" in issue for issue in issues))

    def test_validator_direct_script_entrypoint(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, "tools/validate_frontier_feed.py", "--help"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Frontier Radar V1.2", result.stdout)

    def test_failed_quality_gate_preserves_last_known_good_feed(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "feed.json"
            status = Path(tmp) / "status.json"
            original = {"schema_version": "legacy", "feed_sha256": "bootstrap"}
            output.write_text(json.dumps(original), encoding="utf-8")
            bad = self.valid_feed()
            bad["healthy_source_count"] = 0
            payload = dict(bad)
            payload.pop("feed_sha256")
            bad["feed_sha256"] = sha256_json(payload)
            with patch("tools.frontier_radar.build_feed", return_value=bad):
                with self.assertRaises(ScanQualityError):
                    write_feed(output, status)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), original)
            status_payload = json.loads(status.read_text(encoding="utf-8"))
            self.assertFalse(status_payload["healthy"])
            self.assertTrue(status_payload["preserved_previous"])
            self.assertFalse((Path(tmp) / "feed.sha256").exists())


if __name__ == "__main__":
    unittest.main()
