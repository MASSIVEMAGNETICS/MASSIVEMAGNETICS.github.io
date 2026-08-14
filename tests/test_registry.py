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


if __name__ == "__main__":
    unittest.main()
