from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from build_site import build  # noqa: E402


class BHeardBoardAlphaTests(unittest.TestCase):
    def test_board_source_is_available_but_not_an_artist_subpage(self) -> None:
        board = ROOT / "network" / "board" / "index.html"
        board_js = ROOT / "network" / "board" / "board.js"
        board_css = ROOT / "network" / "board" / "board.css"
        self.assertTrue(board.is_file())
        self.assertTrue(board_js.is_file())
        self.assertTrue(board_css.is_file())

        html = board.read_text(encoding="utf-8")
        script = board_js.read_text(encoding="utf-8")
        self.assertIn("B Heard Board Alpha", html)
        self.assertIn("MASSIVEMAGNETICS/MASSIVEMAGNETICS.github.io", script)
        self.assertIn("/issues?state=all", script)

        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / "site"
            build(site)
            for route in ("beheardnetwork", "bheardnetwork", "network"):
                self.assertFalse((site / route).exists(), f"B Heard route leaked onto artist origin: {route}")
            homepage = (site / "index.html").read_text(encoding="utf-8")
            self.assertIn('href="https://bheardnetwork.com/"', homepage)
            sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")
            self.assertNotIn("https://iambandobandz.com/network/", sitemap)

    def test_board_does_not_claim_final_account_backend(self) -> None:
        html = (ROOT / "network" / "board" / "index.html").read_text(encoding="utf-8")
        self.assertIn("No fake engagement", html)
        self.assertIn("no claim that this is the final account backend", html)
        self.assertIn("public GitHub data", html)


if __name__ == "__main__":
    unittest.main()
