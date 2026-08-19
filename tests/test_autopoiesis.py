from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_site import build
from registry_lib import build_autopoiesis_manifest, load_registry
from validate_registry import validate_built_site


class AutopoiesisTests(unittest.TestCase):
    def test_policy_has_bounded_mutation_boundary(self) -> None:
        policy = load_registry()["autopoiesis"]
        self.assertEqual(policy["architecture"], "bounded-autopoiesis-v1")
        self.assertTrue(policy["boundary"]["same_origin_runtime"])
        self.assertTrue(policy["boundary"]["private_registry_excluded"])
        forbidden = set(policy["repair"]["forbidden_autonomous_mutations"])
        self.assertTrue({"identity", "legal-policy", "pricing", "source-code", "private-data"}.issubset(forbidden))

    def test_manifest_is_derived_from_canonical_genome(self) -> None:
        registry = load_registry()
        manifest = build_autopoiesis_manifest(registry)
        self.assertEqual(manifest["canonical_origin"], "https://iambandobandz.com/")
        self.assertEqual(len(manifest["proof"]["genome_sha256"]), 64)
        self.assertEqual(len(manifest["proof"]["autopoiesis_policy_sha256"]), 64)

    def test_built_site_contains_recovery_organs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / "site"
            build(site)
            self.assertEqual(validate_built_site(site), [])
            manifest = json.loads((site / ".well-known" / "autopoiesis.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["architecture"], "bounded-autopoiesis-v1")
            self.assertTrue((site / "sw.js").is_file())
            self.assertTrue((site / "autopoietic-runtime.js").is_file())

    def test_every_rendered_page_receives_continuity_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / "site"
            build(site)
            tag = '<script src="/autopoietic-runtime.js" defer></script>'
            pages = list(site.rglob("*.html"))
            self.assertGreater(len(pages), 3)
            for page in pages:
                self.assertIn(tag, page.read_text(encoding="utf-8"), str(page))

    def test_service_worker_refuses_cross_origin_repair(self) -> None:
        worker = (ROOT / "sw.js").read_text(encoding="utf-8")
        self.assertIn("url.origin !== self.location.origin", worker)
        self.assertIn("LKG_SERVED", worker)
        self.assertNotIn("contents: write", worker)


if __name__ == "__main__":
    unittest.main()
