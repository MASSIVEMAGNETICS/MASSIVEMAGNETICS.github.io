from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_site import build
from registry_lib import build_jsonld, load_registry
from validate_registry import validate_built_site, validate_source


class RegistryTests(unittest.TestCase):
    def test_source_registry_is_consistent(self) -> None:
        self.assertEqual(validate_source(), [])

    def test_jsonld_contains_canonical_artist_and_person(self) -> None:
        graph = build_jsonld(load_registry())["@graph"]
        names = {node["name"] for node in graph}
        self.assertIn("Brandon Emery", names)
        self.assertIn("iambandobandz", names)
        self.assertNotIn("Bando Bandz", json.dumps(graph))

    def test_build_is_sanitized_and_self_consistent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / "site"
            build(site)
            self.assertEqual(validate_built_site(site), [])
            self.assertFalse((site / "registry" / "private").exists())
            manifest = json.loads((site / ".well-known" / "iambandobandz.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["canonical_brand"], "iambandobandz")
            self.assertEqual(manifest["canonical_domain"], "https://iambandobandz.com/")

    def test_empire_revenue_routes_survive_sanitized_build(self) -> None:
        audit_url = "https://book.stripe.com/eVqfZg8nz3Ys0LT8uZgbm01"
        bheard_url = "https://buy.stripe.com/14AaEWgU5dz23Y5aD7gbm09"
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / "site"
            build(site)

            index = (site / "index.html").read_text(encoding="utf-8")
            network_path = site / "network" / "index.html"
            network_thanks = site / "network" / "thanks" / "index.html"
            store_path = site / "store" / "index.html"
            store_thanks = site / "store" / "thanks" / "index.html"
            commerce_path = site / "store" / "commerce.json"

            self.assertIn(audit_url, index)
            self.assertIn('href="/store/"', index)
            self.assertNotIn("https://iambandobandz.store/", index)
            self.assertIn('href="/network/"', index)

            self.assertTrue(network_path.is_file(), "B Heard /network/ route was omitted from deploy artifact")
            self.assertTrue(network_thanks.is_file(), "B Heard post-checkout route was omitted from deploy artifact")
            network = network_path.read_text(encoding="utf-8")
            self.assertIn("$9.99", network)
            self.assertIn(bheard_url, network)
            self.assertIn("Secure Stripe checkout active", network)
            self.assertNotIn("fails closed", network)

            self.assertTrue(store_path.is_file(), "Direct /store/ route was omitted from deploy artifact")
            self.assertTrue(store_thanks.is_file(), "Store post-checkout route was omitted from deploy artifact")
            self.assertTrue(commerce_path.is_file(), "Store commerce registry was omitted from deploy artifact")
            commerce = json.loads(commerce_path.read_text(encoding="utf-8"))
            self.assertEqual(commerce["status"], "active")
            self.assertEqual(commerce["formats"]["digital"]["price_cents"], 999)
            self.assertEqual(commerce["formats"]["cd"]["price_cents"], 1999)
            self.assertEqual(commerce["formats"]["signed_cd"]["price_cents"], 2999)
            for entry in commerce["formats"].values():
                self.assertTrue(entry["checkout_url"].startswith("https://buy.stripe.com/"))

            store_script = (site / "store" / "store.js").read_text(encoding="utf-8")
            self.assertIn("client_reference_id", store_script)
            self.assertIn("checkout_start", store_script)

    def test_lead_api_cutover_is_fail_closed_by_default(self) -> None:
        registry = load_registry()
        capture = registry["profile"]["lead_capture"]
        self.assertFalse(capture["api_enabled"])
        self.assertEqual(capture["api_endpoint"], "https://api.iambandobandz.com/api/v1/leads")
        self.assertEqual(capture["fallback"], "formsubmit")
        self.assertEqual(capture["consent_text_version"], "signal-capture-v1")
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / "site"
            build(site)
            index = (site / "index.html").read_text(encoding="utf-8")
            script = (site / "script.js").read_text(encoding="utf-8")
            self.assertNotIn('name="iambandobandz:lead-api-endpoint"', index)
            self.assertIn('iambandobandz:lead-api-endpoint', script)
            self.assertIn('https://formsubmit.co/ajax/bandobandz440@gmail.com', script)
            self.assertIn('signal-capture-v1', script)


if __name__ == "__main__":
    unittest.main()
