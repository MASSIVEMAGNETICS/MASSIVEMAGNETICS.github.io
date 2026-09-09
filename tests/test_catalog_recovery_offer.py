import json
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_site import build


class CatalogRecoveryOfferTests(unittest.TestCase):
    def setUp(self) -> None:
        self.offer = json.loads(
            (ROOT / "catalog-recovery" / "offer.json").read_text(encoding="utf-8")
        )

    def test_offer_is_bounded_and_truthful_while_checkout_is_pending(self) -> None:
        self.assertEqual(self.offer["offer_code"], "catalog_recovery_founding_79")
        self.assertEqual(self.offer["price_cents"], 7900)
        self.assertEqual(self.offer["currency"], "USD")
        self.assertEqual(self.offer["billing"], "one_time")
        self.assertEqual(self.offer["scope"]["catalog_roots"], 1)
        self.assertEqual(self.offer["scope"]["maximum_audio_files"], 10000)
        self.assertFalse(self.offer["scope"]["source_audio_uploaded"])
        self.assertFalse(self.offer["scope"]["source_audio_modified"])
        self.assertEqual(self.offer["status"], "checkout_pending")
        self.assertEqual(self.offer["checkout"]["status"], "pending_live_payment_link")
        self.assertIsNone(self.offer["checkout"]["checkout_url"])
        self.assertEqual(urlparse(self.offer["request_url"]).scheme, "mailto")

    def test_page_fails_closed_and_explains_price_refund_and_limits(self) -> None:
        page = (ROOT / "catalog-recovery" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "catalog-recovery" / "offer.js").read_text(encoding="utf-8")
        self.assertIn("$79", page)
        self.assertIn("Up to 10,000 supported audio files", page)
        self.assertIn("Live purchase link pending", page)
        self.assertIn("Request a founding session", page)
        self.assertIn("A completed usable catalog is not refundable", page)
        self.assertNotIn("Secure Stripe checkout active", page)
        self.assertIn("isStripePaymentLink", script)
        self.assertIn("offer.status === 'active'", script)
        self.assertIn("request-only", script)

    def test_sanitized_build_contains_offer_intake_legal_and_analytics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary) / "site"
            build(site)
            for relative in (
                "catalog-recovery/index.html",
                "catalog-recovery/offer.json",
                "catalog-recovery/offer.js",
                "catalog-recovery/thanks/index.html",
                "catalog-recovery/terms/index.html",
                "catalog-recovery/privacy/index.html",
            ):
                self.assertTrue((site / relative).is_file(), relative)
            page = (site / "catalog-recovery" / "index.html").read_text(encoding="utf-8")
            self.assertIn('src="/analytics.js"', page)
            sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")
            self.assertIn("https://iambandobandz.com/catalog-recovery/", sitemap)


if __name__ == "__main__":
    unittest.main()
