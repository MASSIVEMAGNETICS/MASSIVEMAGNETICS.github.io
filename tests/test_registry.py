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
        self.assertIn("IAMBANDOBANDZ", names)

    def test_build_is_sanitized_and_self_consistent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / "site"
            build(site)
            self.assertEqual(validate_built_site(site), [])
            self.assertFalse((site / "registry" / "private").exists())
            manifest = json.loads((site / ".well-known" / "iambandobandz.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["canonical_domain"], "https://iambandobandz.com/")

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
