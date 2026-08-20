from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import sys
sys.path.insert(0, str(ROOT / "tools"))
from build_site import ANALYTICS_PAGES, build


class OwnerAnalyticsTests(unittest.TestCase):
    def test_owner_dashboard_source_is_noindex_and_counter_complete(self) -> None:
        page = (ROOT / "owner" / "analytics" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "owner" / "analytics" / "dashboard.js").read_text(encoding="utf-8")
        self.assertIn('noindex,nofollow,noarchive', page)
        for counter in ("kpiViews", "kpiSessions", "kpiRevenue", "kpiCheckout", "kpiMusic", "kpiLeads"):
            self.assertIn(f'id="{counter}"', page)
        self.assertIn("EXPORT JSON", page)
        self.assertIn("EXPORT CSV", page)
        self.assertIn("IMPORT EVENTS", page)
        self.assertIn("LOCAL BROWSER DATA", page)
        self.assertIn("Site-wide collector: not connected", script)
        self.assertIn("iambandobandz_click_events", script)

    def test_shared_analytics_schema_supports_sessions_and_future_collector(self) -> None:
        script = (ROOT / "analytics.js").read_text(encoding="utf-8")
        self.assertIn("iambandobandz_session_id", script)
        self.assertIn("session_id", script)
        self.assertIn("page_view", script)
        self.assertIn("revenue_path_click", script)
        self.assertIn("checkout_start", script)
        self.assertIn('meta[name="iambandobandz:analytics-endpoint"]', script)
        self.assertIn("local-browser-only", script)

    def test_homepage_emits_page_views_with_session_identity(self) -> None:
        script = (ROOT / "script.js").read_text(encoding="utf-8")
        self.assertIn("analyticsSessionKey = 'iambandobandz_session_id'", script)
        self.assertIn("session_id: analyticsSessionId()", script)
        self.assertIn("track('page_view')", script)
        self.assertIn("slice(-2000)", script)

    def test_sanitized_build_contains_owner_dashboard_and_shared_tracking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / "site"
            build(site)
            self.assertTrue((site / "owner" / "index.html").is_file())
            self.assertTrue((site / "owner" / "analytics" / "index.html").is_file())
            self.assertTrue((site / "owner" / "analytics" / "dashboard.js").is_file())
            self.assertTrue((site / "analytics.js").is_file())

            owner = (site / "owner" / "index.html").read_text(encoding="utf-8")
            self.assertIn('href="/owner/analytics/"', owner)
            dashboard = (site / "owner" / "analytics" / "index.html").read_text(encoding="utf-8")
            self.assertIn("noindex,nofollow,noarchive", dashboard)

            for relative in ANALYTICS_PAGES:
                page = (site / relative).read_text(encoding="utf-8")
                self.assertIn('src="/analytics.js"', page, relative)

    def test_owner_dashboard_is_not_in_public_sitemap_registry(self) -> None:
        profile = (ROOT / "registry" / "public" / "public-profile.json").read_text(encoding="utf-8")
        self.assertNotIn('/owner/', profile)
        self.assertNotIn('/owner/analytics/', profile)


if __name__ == "__main__":
    unittest.main()
