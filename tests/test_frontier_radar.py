from __future__ import annotations

import unittest
from datetime import datetime, timezone

from tools.frontier_radar import RadarItem, dedupe, evidence_hash, score_item, text_signal_score, traction_score


class FrontierRadarTests(unittest.TestCase):
    def item(self, **overrides):
        base = dict(
            source="github",
            external_id="1",
            title="tiny continual learning world model",
            url="https://example.test/repo",
            summary="offline sparse agent with memory and compression",
            author="indie",
            published_at="2026-08-20T00:00:00Z",
            updated_at="2026-08-20T00:00:00Z",
            metrics={"stars": 100, "forks": 10},
            indie_hint=1.0,
            reproducibility_hint=0.95,
            query="continual learning",
        )
        base.update(overrides)
        return RadarItem(**base)

    def test_frontier_terms_raise_signal(self):
        self.assertGreater(text_signal_score("continual learning world model", "sparse memory"), 0.5)
        self.assertEqual(text_signal_score("cooking notes", "banana bread"), 0.0)

    def test_traction_is_bounded(self):
        self.assertGreaterEqual(traction_score({"stars": 999999}), 0.0)
        self.assertLessEqual(traction_score({"stars": 999999}), 1.0)

    def test_scoring_is_bounded_and_hashes(self):
        now = datetime(2026, 8, 21, tzinfo=timezone.utc)
        scored = score_item(self.item(), now=now)
        self.assertGreater(scored.score, 50)
        self.assertLessEqual(scored.score, 100)
        self.assertEqual(len(scored.evidence_sha256), 64)
        self.assertEqual(scored.evidence_sha256, evidence_hash(scored))

    def test_dedupe_keeps_highest_score(self):
        low = self.item(score=10.0)
        high = self.item(score=90.0)
        result = dedupe([low, high])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].score, 90.0)


if __name__ == "__main__":
    unittest.main()
