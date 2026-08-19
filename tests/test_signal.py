from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_site import build
from registry_lib import load_registry


class SignalExperimentTests(unittest.TestCase):
    def test_signal_route_is_registered(self) -> None:
        routes = {route["path"] for route in load_registry()["profile"]["routes"]}
        self.assertIn("/signal/", routes)

    def test_signal_survives_sanitized_build(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / "site"
            build(site)
            page = site / "signal" / "index.html"
            self.assertTrue(page.is_file(), "THE SIGNAL route was omitted from deploy artifact")
            html = page.read_text(encoding="utf-8")
            self.assertIn("THE SIGNAL", html)
            self.assertIn("What have you been seeing that you cannot make other people see?", html)
            self.assertIn('id="door" class="door reveal" hidden', html)
            self.assertIn("KEEP LOCAL ONLY", html)
            self.assertIn("SHA-256", html)
            self.assertIn("https://formsubmit.co/ajax/bandobandz440@gmail.com", html)
            self.assertNotIn("peer-responses", html)

    def test_sitemap_contains_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / "site"
            build(site)
            sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")
            self.assertIn("https://iambandobandz.com/signal/", sitemap)


if __name__ == "__main__":
    unittest.main()
