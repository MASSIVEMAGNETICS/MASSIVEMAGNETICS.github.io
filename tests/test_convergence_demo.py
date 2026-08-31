from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ConvergenceDemoTests(unittest.TestCase):
    def test_public_route_files_exist(self) -> None:
        for relative in [
            "convergence/index.html",
            "convergence/styles.css",
            "convergence/app.js",
        ]:
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_build_publishes_and_instruments_route(self) -> None:
        build = (ROOT / "tools" / "build_site.py").read_text(encoding="utf-8")
        self.assertIn('"convergence",', build)
        self.assertIn('"convergence/index.html",', build)

    def test_demo_is_read_only_and_public_scope(self) -> None:
        app = (ROOT / "convergence" / "app.js").read_text(encoding="utf-8")
        self.assertIn("https://api.github.com/users/${USER}/repos", app)
        self.assertIn("Promise.allSettled", app)
        self.assertIn("failed closed", app)
        self.assertNotIn("Authorization:", app)
        self.assertNotIn("GITHUB_TOKEN", app)
        self.assertNotIn("method:'POST'", app)
        self.assertNotIn('method: "POST"', app)
        self.assertNotIn("api.github.com/repos/${USER}", app)

    def test_demo_preserves_claim_and_human_boundaries(self) -> None:
        page = (ROOT / "convergence" / "index.html").read_text(encoding="utf-8")
        app = (ROOT / "convergence" / "app.js").read_text(encoding="utf-8")
        self.assertIn("No autonomous merges", page)
        self.assertIn("No claim is upgraded beyond its source evidence", page)
        self.assertIn("human approval required", app)
        self.assertIn("No recommendation was manufactured", app)


if __name__ == "__main__":
    unittest.main()
