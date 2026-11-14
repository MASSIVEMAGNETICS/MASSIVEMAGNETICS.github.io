from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_bheard_site  # noqa: E402


class BHeardIndependentSiteBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temp.name) / "site"
        build_bheard_site.build(cls.output)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def read(self, relative: str) -> str:
        return (self.output / relative).read_text(encoding="utf-8")

    def test_independent_routes_and_required_assets_exist(self) -> None:
        expected = (
            "index.html",
            "styles.css",
            "brand.css",
            "analytics.js",
            "_headers",
            "robots.txt",
            "assets/bheard-network-logo.svg",
            "network/index.html",
            "network/offer.json",
            "network/board/index.html",
            "network/board/board.css",
            "network/board/board.js",
            "network/thanks/index.html",
        )
        for relative in expected:
            with self.subTest(path=relative):
                self.assertTrue((self.output / relative).is_file(), relative)

    def test_canonical_urls_and_cross_site_navigation_are_independent(self) -> None:
        home = self.read("index.html")
        promo = self.read("network/index.html")
        board = self.read("network/board/index.html")

        self.assertIn('href="https://bheardnetwork.com/"', home)
        self.assertIn('href="https://bheardnetwork.com/network/"', promo)
        self.assertIn('href="https://bheardnetwork.com/network/board/"', board)
        for page in (home, promo, board):
            self.assertNotIn("iambandobandz.com/beheardnetwork/", page)
            self.assertIn('href="https://iambandobandz.com/"', page)
            self.assertIn('src="/assets/bheard-network-logo.svg"', page)
        self.assertIn('href="/network/board/"', home)
        self.assertIn('href="/network/"', home)
        self.assertIn('href="https://iambandobandz.com/privacy/"', board)
        self.assertIn('href="https://iambandobandz.com/terms/"', board)
        self.assertNotIn('href="/proof/"', home)
        self.assertNotIn('href="/proof/"', promo)
        self.assertNotIn('href="/proof/"', board)
        self.assertIn('href="https://iambandobandz.com/proof/"', promo)

    def test_unverified_member_count_is_not_published_in_source_or_build(self) -> None:
        source_home = (ROOT / "beheardnetwork" / "index.html").read_text(encoding="utf-8")
        home = self.read("index.html")
        self.assertNotIn("20,000-member", source_home)
        self.assertNotIn("20,000-member", home)
        self.assertIn("community for independent artists", source_home)
        self.assertIn("community for independent artists", home)

    def test_canonical_logo_uses_red_black_white_globe_and_headphones(self) -> None:
        logo = self.read("assets/bheard-network-logo.svg")
        for token in ("B HEARD", "NETWORK", "#D71920", "#FFFFFF", "#090909", "<ellipse", "<rect"):
            with self.subTest(token=token):
                self.assertIn(token, logo)

    def test_offer_registry_uses_independent_canonical_path(self) -> None:
        offer = json.loads(self.read("network/offer.json"))
        self.assertEqual(offer["offer_code"], "bheard_creator_promo_v1")
        self.assertEqual(offer["price_cents"], 999)
        self.assertEqual(offer["canonical_path"], "https://bheardnetwork.com/network/")

    def test_board_is_explicitly_github_backed_not_first_party_auth(self) -> None:
        board = self.read("network/board/index.html")
        script = self.read("network/board/board.js")
        self.assertIn("free GitHub account", board)
        self.assertIn("const REPO = 'MASSIVEMAGNETICS/MASSIVEMAGNETICS.github.io';", script)
        self.assertIn("https://api.github.com/repos/${REPO}/issues", script)
        self.assertNotIn("Authorization:", script)

    def test_analytics_is_bheard_scoped_and_browser_local_by_default(self) -> None:
        analytics = self.read("analytics.js")
        self.assertIn("bheard_click_events", analytics)
        self.assertIn("bheard_session_id", analytics)
        self.assertIn("window.BHeardAnalytics", analytics)
        self.assertIn("local-browser-only", analytics)
        self.assertIn("bheard:analytics-endpoint", analytics)
        self.assertNotIn("iambandobandz_click_events", analytics)

    def test_checkout_return_is_explicitly_unverified_and_not_a_payment_event(self) -> None:
        page = self.read("network/thanks/index.html")
        self.assertIn('content="noindex,nofollow"', page)
        self.assertIn("This page cannot confirm whether a payment succeeded.", page)
        self.assertIn("only after payment and required information are independently verified", page)
        self.assertIn("event: 'checkout_return_unverified'", page)
        self.assertNotIn("That receipt is the payment record.", page)
        self.assertNotIn("event: 'checkout_return'", page)
        self.assertNotIn("payment_verified", page)
        self.assertIn("B HEARD NETWORK", page)

    def test_checkout_return_boundary_upgrades_legacy_and_accepts_safe_source(self) -> None:
        legacy = "\n".join((
            f"<p>{build_bheard_site.LEGACY_CHECKOUT_COPY}</p>",
            f"<p>{build_bheard_site.LEGACY_INTAKE_COPY}</p>",
            build_bheard_site.LEGACY_CHECKOUT_EVENT,
        ))
        expected = "\n".join((
            f"<p>{build_bheard_site.SAFE_CHECKOUT_COPY}</p>",
            f"<p>{build_bheard_site.SAFE_INTAKE_COPY}</p>",
            build_bheard_site.SAFE_CHECKOUT_EVENT,
        ))
        self.assertEqual(build_bheard_site.enforce_checkout_return_boundary(legacy), expected)
        self.assertEqual(build_bheard_site.enforce_checkout_return_boundary(expected), expected)

    def test_checkout_return_boundary_rejects_missing_or_ambiguous_anchors(self) -> None:
        safe_copy = f"<p>{build_bheard_site.SAFE_CHECKOUT_COPY}</p>"
        legacy_copy = f"<p>{build_bheard_site.LEGACY_CHECKOUT_COPY}</p>"
        with self.assertRaises(RuntimeError):
            build_bheard_site.enforce_checkout_return_boundary(safe_copy)
        with self.assertRaises(RuntimeError):
            build_bheard_site.enforce_checkout_return_boundary(
                legacy_copy + safe_copy + "\n" +
                f"<p>{build_bheard_site.LEGACY_INTAKE_COPY}</p>\n" +
                build_bheard_site.LEGACY_CHECKOUT_EVENT
            )

    def test_baseline_security_headers_are_present(self) -> None:
        headers = self.read("_headers")
        for header in (
            "X-Content-Type-Options: nosniff",
            "Referrer-Policy: strict-origin-when-cross-origin",
            "X-Frame-Options: DENY",
            "Permissions-Policy: camera=(), microphone=(), geolocation=()",
        ):
            with self.subTest(header=header):
                self.assertIn(header, headers)

    def test_build_is_repeatable_and_refuses_unmarked_output(self) -> None:
        build_bheard_site.build(self.output)
        self.assertTrue((self.output / ".bheard-build").is_file())

        unmarked = Path(self.temp.name) / "user-data"
        unmarked.mkdir()
        (unmarked / "keep.txt").write_text("keep", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            build_bheard_site.build(unmarked)
        self.assertEqual((unmarked / "keep.txt").read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
