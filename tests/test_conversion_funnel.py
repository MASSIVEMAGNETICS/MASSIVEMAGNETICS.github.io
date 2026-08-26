from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ConversionFunnelTests(unittest.TestCase):
    def test_homepage_preserves_truth_compiler_without_making_it_global_consumer_cta(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="/audit/"', index)
        self.assertIn('RUN THE TRUTH COMPILER', index)
        self.assertIn('SEE EVIDENCE + START', index)
        self.assertIn('data-loop-stage="consider"', index)
        self.assertIn('data-revenue-path="truth-compiler"', index)
        self.assertNotIn('Inspect $97 audit', index)
        self.assertNotIn('See the $97 repo audit', index)

    def test_homepage_keeps_one_high_intent_direct_checkout_path(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertEqual(index.count('https://book.stripe.com/eVqfZg8nz3Ys0LT8uZgbm01'), 1)
        self.assertIn('Buy now — $97', index)

    def test_homepage_revenue_cards_have_defined_contrast_tokens(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('--signal:var(--rust)', index)
        self.assertIn('--muted:var(--steel)', index)
        self.assertIn('.revenue-card{color:var(--paper)}', index)

    def test_homepage_artwork_wall_is_not_a_front_door_dependency(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('class="release-gallery"', index)
        self.assertIn('href="/store/"', index)

    def test_consumer_navigation_prioritizes_working_owned_surfaces(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        for route in ('/store/', '/network/', '/proof/', '/research/'):
            self.assertIn(f'href="{route}"', index)
        self.assertIn('href="#listen"', index)
        self.assertIn('href="#contact"', index)

    def test_research_and_experimental_surfaces_remain_reachable_and_indexable(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        profile = json.loads((ROOT / "registry" / "public" / "public-profile.json").read_text(encoding="utf-8"))
        routes = {item["path"] for item in profile["routes"]}
        self.assertIn('/audit/', routes)
        self.assertIn('/signal/', routes)
        self.assertIn('href="/audit/"', index)

    def test_registry_generates_commercial_routes_and_preserves_pinned_consent(self) -> None:
        profile = json.loads((ROOT / "registry" / "public" / "public-profile.json").read_text(encoding="utf-8"))
        routes = {item["path"] for item in profile["routes"]}
        for route in ('/audit/', '/store/', '/network/', '/signal/', '/proof/', '/research/'):
            self.assertIn(route, routes)
        self.assertEqual(profile["lead_capture"]["consent_text_version"], "signal-capture-v1")

    def test_internal_revenue_routes_remain_measurable(self) -> None:
        script = (ROOT / "script.js").read_text(encoding="utf-8")
        self.assertIn("document.querySelectorAll('a[href]')", script)
        self.assertIn("page_path: location.pathname", script)
        self.assertIn("utm_campaign", script)
        self.assertIn("data-revenue-path", (ROOT / "index.html").read_text(encoding="utf-8"))

    def test_music_capture_is_not_on_first_outbound_click(self) -> None:
        script = (ROOT / "script.js").read_text(encoding="utf-8")
        self.assertIn("signal_music_engagement_count", script)
        self.assertIn("if (priorMusicEngagements < 1) return;", script)
        self.assertIn("signal-capture-v1", script)
        self.assertIn('class="consent-legal"', script)
        self.assertIn('href="/privacy/"', script)
        self.assertIn('href="/terms/"', script)

    def test_b_heard_offer_states_bounded_success_condition(self) -> None:
        network = (ROOT / "network" / "index.html").read_text(encoding="utf-8")
        self.assertIn("YOU PAY FOR THE WORK", network)
        self.assertIn("Actions + evidence", network)
        self.assertIn("not guaranteed", network)
        self.assertIn('href="/privacy/"', network)
        self.assertIn('href="/terms/"', network)

\n
    def test_storefront_revenue_contract_is_active_and_attributed(self) -> None:
        commerce = json.loads((ROOT / "store" / "commerce.json").read_text(encoding="utf-8"))
        assets = json.loads((ROOT / "store" / "assets" / "assets.json").read_text(encoding="utf-8"))
        store_js = (ROOT / "store" / "store.js").read_text(encoding="utf-8")

        self.assertEqual(commerce["status"], "active")
        self.assertEqual(set(commerce["formats"]), {"digital", "cd", "signed_cd"})
        self.assertTrue(
            all(
                details["checkout_url"].startswith("https://buy.stripe.com/")
                for details in commerce["formats"].values()
            )
        )

        products = {product["sku"]: product for product in assets["products"]}
        self.assertEqual(set(commerce["catalog_skus"]), set(products))
        checkout_count = sum(
            1
            for sku in commerce["catalog_skus"]
            for format_name in products[sku]["formats"]
            if format_name in commerce["formats"]
        )
        self.assertEqual(checkout_count, 18)
        for token in ("COMMERCE_REGISTRY_URL", "client_reference_id", "buy.stripe.com", "data-checkout"):
            self.assertIn(token, store_js)

    def test_custom_deploy_recovers_after_automated_pages_publish(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        self.assertIn('"Frontier Radar Refresh"', workflow)
        self.assertIn('"pages build and deployment"', workflow)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", workflow)
        self.assertIn("ref: main", workflow)


if __name__ == "__main__":
    unittest.main()
