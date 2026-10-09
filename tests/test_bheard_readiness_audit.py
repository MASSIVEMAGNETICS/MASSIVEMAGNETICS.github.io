from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from audit_bheard_readiness import audit  # noqa: E402


class BHeardReadinessAuditTests(unittest.TestCase):
    def test_source_classifications_are_not_live_certification(self) -> None:
        report = audit(ROOT)
        self.assertEqual(report["frontend_source"], "CANDIDATE")
        self.assertEqual(report["independent_origin"], "BLOCKED")
        self.assertEqual(report["board_identity"], "GITHUB_ALPHA")
        self.assertEqual(report["live_dns_tls_uptime"], "UNKNOWN")
        self.assertEqual(report["remote_analytics_collector"], "BLOCKED")

    def test_missing_and_invalid_files_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = audit(root)
            self.assertEqual(report["frontend_source"], "BLOCKED")
            self.assertEqual(report["independent_origin"], "UNKNOWN")
            self.assertEqual(report["stripe_link_source"], "BLOCKED")

            offer = root / "network" / "offer.json"
            offer.parent.mkdir(parents=True)
            offer.write_text("{invalid", encoding="utf-8")
            self.assertEqual(audit(root)["stripe_link_source"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
