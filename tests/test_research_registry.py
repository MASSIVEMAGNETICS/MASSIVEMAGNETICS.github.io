from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_site import build

REGISTRY = ROOT / "registry" / "public" / "research.json"
HEX64 = re.compile(r"[0-9a-f]{64}")


def canonical_sha256(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def root_sha256(records: list[dict]) -> str:
    material = "".join(
        f"{record['id']}:{record['record_sha256']}\n"
        for record in sorted(records, key=lambda item: item["id"])
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class ResearchRegistryTests(unittest.TestCase):
    def load(self) -> dict:
        return json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_record_hashes_and_root_are_consistent(self) -> None:
        registry = self.load()
        records = registry["records"]
        self.assertEqual(len(records), 13)
        self.assertEqual(len({r["id"] for r in records}), 13)
        for record in records:
            stored = record["record_sha256"]
            self.assertRegex(stored, HEX64)
            payload = dict(record)
            payload.pop("record_sha256")
            self.assertEqual(stored, canonical_sha256(payload), record["id"])
            for artifact in record.get("artifacts", []):
                self.assertRegex(artifact["sha256"], HEX64)
                self.assertGreater(artifact["bytes"], 0)
        self.assertEqual(registry["proof"]["root_sha256"], root_sha256(records))

    def test_counts_and_epistemic_classes_are_pinned(self) -> None:
        registry = self.load()
        records = registry["records"]
        counts = registry["counts"]
        self.assertEqual(counts["registered_records"], 13)
        for cls, expected in (("materialized", 7), ("active", 2), ("legacy", 3), ("deprecated", 1)):
            self.assertEqual(sum(r["class"] == cls for r in records), expected)
            if cls != "deprecated":
                self.assertEqual(counts[cls], expected)
        self.assertEqual(counts["deprecated_whitepapers"], 14)
        self.assertEqual(counts["listed_whitepapers"], 26)
        self.assertEqual(counts["materialized_artifacts"], 8)
        self.assertTrue(all(not a.get("public", False) for r in records if r["class"] == "deprecated" for a in r.get("artifacts", [])))

    def test_research_route_survives_sanitized_build(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / "site"
            build(site)
            self.assertTrue((site / "research" / "index.html").is_file())
            self.assertTrue((site / "research" / "research.css").is_file())
            script = (site / "research" / "research.js").read_text(encoding="utf-8")
            self.assertIn("crypto.subtle.digest", script)
            self.assertIn("/registry/public/research.json", script)
            built_registry = json.loads((site / "registry" / "public" / "research.json").read_text(encoding="utf-8"))
            self.assertEqual(built_registry["proof"]["root_sha256"], self.load()["proof"]["root_sha256"])
            sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")
            self.assertIn("https://iambandobandz.com/research/", sitemap)


if __name__ == "__main__":
    unittest.main()
