from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_site import build
from registry_lib import load_registry
from validate_registry import validate_built_site, validate_proof_ledger, validate_source


class ProofLedgerTests(unittest.TestCase):
    def test_source_ledger_is_bounded_and_valid(self) -> None:
        ledger_path = ROOT / "proof" / "ledger.json"
        self.assertEqual(validate_proof_ledger(ledger_path), [])
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(ledger["entries"]), 10)
        self.assertIn("claim_boundary", ledger["methodology"])
        for entry in ledger["entries"]:
            self.assertTrue(entry["evidence"])
            self.assertIn(entry["status"], {"VERIFIED", "PARTIAL"})
            for evidence in entry["evidence"]:
                self.assertTrue(evidence["url"].startswith("https://"))

    def test_proof_route_is_canonical(self) -> None:
        routes = {route["path"] for route in load_registry()["profile"]["routes"]}
        self.assertIn("/proof/", routes)
        self.assertEqual(validate_source(), [])

    def test_sanitized_build_contains_proof_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / "site"
            build(site)
            self.assertEqual(validate_built_site(site), [])
            proof_html = (site / "proof" / "index.html").read_text(encoding="utf-8")
            homepage = (site / "index.html").read_text(encoding="utf-8")
            sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")
            self.assertIn("THE WORK EXISTS", proof_html)
            self.assertIn("/proof/ledger.json", proof_html)
            self.assertIn('href="/proof/"', homepage)
            self.assertIn("https://iambandobandz.com/proof/", sitemap)


if __name__ == "__main__":
    unittest.main()
