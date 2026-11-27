from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_bheard_site  # noqa: E402
import build_site  # noqa: E402


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

    def test_independent_landing_and_promo_pages_publish_only_from_independent_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            artist_output = Path(temp) / "artist-site"
            build_site.build(artist_output)

            self.assertFalse((artist_output / "beheardnetwork").exists())
            # The legacy social-app prototype must not leak back onto the artist origin.
            self.assertFalse((artist_output / "bheardnetwork").exists())
            self.assertFalse((artist_output / "network").exists())

            homepage = (artist_output / "index.html").read_text(encoding="utf-8")
            self.assertNotIn('href="/network/"', homepage)
            self.assertIn('href="https://bheardnetwork.com/"', homepage)

            identity = json.loads((artist_output / "identity.jsonld").read_text(encoding="utf-8"))
            bheard = next(
                (
                    item for item in identity.get("@graph", [])
                    if item.get("@type") == "Organization" and item.get("name") == "B Heard Network"
                ),
                None,
            )
            self.assertIsNotNone(bheard)
            self.assertEqual(bheard.get("url"), "https://bheardnetwork.com/")

        # The separate B Heard builder still publishes these routes at its own root.
        self.assertTrue((self.output / "index.html").is_file())
        self.assertTrue((self.output / "network" / "index.html").is_file())
        self.assertTrue((self.output / "network" / "board" / "index.html").is_file())

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

    def test_mobile_navigation_is_operable_on_all_independent_routes(self) -> None:
        pages = ("index.html", "network/index.html", "network/board/index.html")
        for relative in pages:
            page = self.read(relative)
            with self.subTest(page=relative):
                self.assertIn('<button class="menu-toggle" type="button"', page)
                self.assertIn('aria-label="Toggle navigation"', page)
                self.assertIn('aria-controls="primary-nav"', page)
                self.assertIn('<nav id="primary-nav" class="nav-links"', page)
                self.assertIn("nav.classList.toggle('open', open)", page)
                self.assertIn("if (event.target.closest('a[href]')) setOpen(false)", page)
                self.assertIn("event.key === 'Escape'", page)

        styles = self.read("styles.css")
        self.assertIn(".menu-toggle{display:block}", styles)
        self.assertIn(".nav-links.open{display:flex}", styles)

    def test_unverified_member_count_is_not_published_in_source_or_build(self) -> None:
        source_home = (ROOT / "beheardnetwork" / "index.html").read_text(encoding="utf-8")
        home = self.read("index.html")
        self.assertNotIn("20,000-member", source_home)
        self.assertNotIn("20,000-member", home)
        self.assertIn("community for independent artists", source_home)
        self.assertIn("community for independent artists", home)

    def test_canonical_logo_uses_red_black_white_globe_headphones_and_waves(self) -> None:
        logo = self.read("assets/bheard-network-logo.svg")
        for token in (
            "B HEARD",
            "NETWORK",
            "#D71920",
            "#FFFFFF",
            "#090909",
            "#BFC3C8",
            'class="broadcast-wave"',
            'id="globe"',
            'id="headphones"',
        ):
            with self.subTest(token=token):
                self.assertIn(token, logo)

    def test_offer_registry_uses_independent_canonical_path(self) -> None:
        offer = json.loads(self.read("network/offer.json"))
        self.assertEqual(offer["offer_code"], "bheard_creator_promo_v1")
        self.assertEqual(offer["price_cents"], 999)
        self.assertEqual(offer["canonical_path"], "https://bheardnetwork.com/network/")

    def test_independent_checkout_is_disabled_until_payment_and_fulfillment_are_verified(self) -> None:
        home = self.read("index.html")
        promo = self.read("network/index.html")
        board = self.read("network/board/index.html")
        thanks = self.read("network/thanks/index.html")
        for page in (home, promo, board, thanks):
            self.assertNotIn("buy.stripe.com/", page)
            self.assertNotIn("checkout_start", page)

        for page in (home, promo, board):
            self.assertIn('href="#campaign-launch-gate"', page)
            self.assertIn('id="campaign-launch-gate"', page)
            self.assertIn("No payment is taken from this independent site.", page)
            self.assertNotIn("handled through secure Stripe checkout", page)

        self.assertNotIn("Secure Stripe checkout active", promo)
        self.assertNotIn("Stripe Checkout collects the creator/project information", promo)
        self.assertNotIn("campaign fields and payment are attached to the order", promo)
        self.assertNotIn("existing $9.99 service remains the paid lane", board)
        self.assertIn("Paid creator-promotion checkout is not enabled on the independent site yet", board)
        self.assertIn('data-board-action="campaign-availability"', board)
        self.assertNotIn('data-board-action="creator-promo"', board)
        self.assertNotIn("Stripe Checkout collects the creator/project information", promo)
        self.assertNotIn("campaign fields and payment are attached to the order", promo)
        self.assertNotIn("checkout_start", promo)

        offer = json.loads(self.read("network/offer.json"))
        self.assertFalse(offer["checkout_enabled"])
        self.assertEqual(offer["checkout_status"], "pending_independent_verification")
        self.assertNotIn("checkout_url", offer["stripe"])

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

    def test_analytics_referrer_is_reduced_to_origin(self) -> None:
        analytics = self.read("analytics.js")
        self.assertIn("function safeReferrer()", analytics)
        self.assertIn("new URL(document.referrer).origin", analytics)
        self.assertIn("referrer: safeReferrer()", analytics)
        self.assertNotIn("referrer: document.referrer", analytics)

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

    def test_baseline_security_headers_use_cloudflare_pages_syntax(self) -> None:
        headers = self.read("_headers")
        lines = headers.splitlines()

        # Cloudflare Pages parses `/*` as a catch-all path pattern. A trailing
        # `*/` is another pattern, not a C-style comment delimiter.
        self.assertGreaterEqual(len(lines), 5)
        self.assertEqual(lines[0].strip(), "/*")
        self.assertNotIn("*/", headers)

        for header in (
            "X-Content-Type-Options: nosniff",
            "Referrer-Policy: strict-origin-when-cross-origin",
            "X-Frame-Options: DENY",
            "Permissions-Policy: camera=(), microphone=(), geolocation=()",
        ):
            with self.subTest(header=header):
                self.assertIn(f"  {header}", lines)

    def test_build_is_repeatable_and_refuses_unmarked_output(self) -> None:
        build_bheard_site.build(self.output)
        self.assertTrue((self.output / ".bheard-build").is_file())

        unmarked = Path(self.temp.name) / "user-data"
        unmarked.mkdir()
        (unmarked / "keep.txt").write_text("keep", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            build_bheard_site.build(unmarked)
        self.assertEqual((unmarked / "keep.txt").read_text(encoding="utf-8"), "keep")



    def test_independent_paid_launch_gates_are_documented(self) -> None:
        deployment = (ROOT / "beheardnetwork" / "README.md").read_text(encoding="utf-8")
        required = (
            "Commercial and fulfillment launch gate",
            "DRAFT / not published",
            "B Heard-specific policy",
            "refund policy",
            "privacy notice",
            "section 8.4",
            "fulfillment owner",
            "Verified paid Checkout Session",
            "Closing receipt",
        )
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, deployment)



    def test_serverless_deployment_runbook_is_explicit_and_fail_closed(self) -> None:
        runbook = (ROOT / "beheardnetwork" / "README.md").read_text(encoding="utf-8")
        required = (
            "Cloudflare Pages",
            "Cloudflare Worker",
            "D1",
            "R2",
            "No home server",
            "no inbound tunnel",
            "500 builds/month",
            "20,000 files/site",
            "25 MiB",
            "100,000 requests/day",
            "10 milliseconds CPU",
            "5 million rows read/day",
            "100,000 rows written/day",
            "10 GB-month",
            "$5/month",
            "checkout_enabled: false",
            "stripe_payment_verified",
            "UNIQUE(submission_id, voter_id)",
            "HttpOnly; Secure; SameSite=Lax",
            "Cloudflare Turnstile",
            "paid_pending_fulfillment",
            "manual fulfillment",
            "credential-routing vulnerability",
            "no remote collector",
            "No DNS",
        )
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, runbook)



if __name__ == "__main__":
    unittest.main()
