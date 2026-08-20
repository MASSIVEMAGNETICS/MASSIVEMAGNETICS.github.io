from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ConversionFunnelTests(unittest.TestCase):
    def test_homepage_routes_cold_audit_traffic_through_evidence_page(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="/audit/"', index)
        self.assertNotIn('https://book.stripe.com/', index)
        self.assertIn('data-revenue-path="truth-compiler"', index)

    def test_homepage_revenue_cards_have_defined_contrast_tokens(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('--signal:var(--rust)', index)
        self.assertIn('--muted:var(--steel)', index)
        self.assertIn('.revenue-card{color:var(--paper)}', index)

    def test_homepage_artwork_wall_is_not_a_front_door_dependency(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('class="release-gallery"', index)
        self.assertIn('href="/store/"', index)

    def test_high_value_public_surfaces_are_first_class_navigation(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        for route in ('/signal/', '/proof/', '/research/', '/audit/', '/store/', '/network/'):
            self.assertIn(f'href="{route}"', index)

    def test_registry_generates_commercial_routes_and_capture_version(self) -> None:
        profile = json.loads((ROOT / "registry" / "public" / "public-profile.json").read_text(encoding="utf-8"))
        routes = {item["path"] for item in profile["routes"]}
        for route in ('/audit/', '/store/', '/network/', '/signal/', '/proof/', '/research/'):
            self.assertIn(route, routes)
        self.assertEqual(profile["lead_capture"]["consent_text_version"], "signal-capture-v2")

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
        self.assertIn('href="/privacy/"', script)
        self.assertIn('href="/terms/"', script)

    def test_b_heard_offer_states_bounded_success_condition(self) -> None:
        network = (ROOT / "network" / "index.html").read_text(encoding="utf-8")
        self.assertIn("YOU PAY FOR THE WORK", network)
        self.assertIn("Actions + evidence", network)
        self.assertIn("not guaranteed", network)
        self.assertIn('href="/privacy/"', network)
        self.assertIn('href="/terms/"', network)


if __name__ == "__main__":
    unittest.main()
