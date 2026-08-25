from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_site import build
from registry_lib import build_jsonld, build_sitemap, load_registry


class SearchIdentityContractTests(unittest.TestCase):
    def test_canonical_brand_contract(self) -> None:
        registry = load_registry()
        entities = {item["id"]: item for item in registry["entities"]["entities"]}
        artist = entities["artist:iambandobandz"]
        site = entities["domain:iambandobandz-com"]
        network = entities["network:b-heard-network"]
        store = entities["store:iambandobandz-store"]

        self.assertEqual(artist["name"], "iambandobandz")
        self.assertEqual(artist["aliases"], [])
        self.assertEqual(artist["canonical_url"], "https://iambandobandz.com/")
        self.assertEqual(site["name"], "iambandobandz")
        self.assertEqual(site["canonical_url"], "https://iambandobandz.com/")
        self.assertEqual(network["canonical_url"], "https://iambandobandz.com/network/")
        self.assertEqual(store["status"], "active")
        self.assertEqual(store["canonical_url"], "https://iambandobandz.com/store/")

    def test_generated_structured_data_has_no_artist_collision(self) -> None:
        graph = build_jsonld(load_registry())
        raw = json.dumps(graph, ensure_ascii=False)
        self.assertIn('"name": "iambandobandz"', raw)
        self.assertNotIn("Bando Bandz", raw)

    def test_deployed_search_surfaces_are_self_consistent(self) -> None:
        registry = load_registry()
        expected_routes = {
            "/",
            "/proof/",
            "/audit/",
            "/research/",
            "/signal/",
            "/store/",
            "/network/",
            "/frontier-radar/",
            "/portfolio/",
            "/jesus-told-me/",
            "/privacy/",
            "/terms/",
        }
        self.assertEqual({row["path"] for row in registry["profile"]["routes"]}, expected_routes)

        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / "site"
            build(site)
            index = (site / "index.html").read_text(encoding="utf-8")
            sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")
            manifest = json.loads((site / "site.webmanifest").read_text(encoding="utf-8"))
            llms = (site / "llms.txt").read_text(encoding="utf-8")

            self.assertIn("<title>iambandobandz — Official Site", index)
            self.assertIn('<link rel="canonical" href="https://iambandobandz.com/">', index)
            self.assertIn('<meta property="og:site_name" content="iambandobandz">', index)
            self.assertNotIn("Bando Bandz", index)
            self.assertNotIn("I AM BANDO BANDZ", index)
            self.assertEqual(sitemap, build_sitemap(registry))
            self.assertEqual(manifest["short_name"], "iambandobandz")
            self.assertIn("Canonical artist/brand: iambandobandz", llms)
            self.assertIn("https://iambandobandz.com/", llms)


if __name__ == "__main__":
    unittest.main()
