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
    def test_board_survives_sanitized_build_and_sitemap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / "site"
            build(site)

            board = site / "network" / "board" / "index.html"
            board_js = site / "network" / "board" / "board.js"
            board_css = site / "network" / "board" / "board.css"

            self.assertTrue(board.is_file())
            self.assertTrue(board_js.is_file())
            self.assertTrue(board_css.is_file())

            html = board.read_text(encoding="utf-8")
            script = board_js.read_text(encoding="utf-8")
            sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")

            self.assertIn(
                '<link rel="canonical" href="https://iambandobandz.com/network/board/">',
                html,
            )
            self.assertIn("B Heard Board Alpha", html)
            self.assertIn("MASSIVEMAGNETICS/MASSIVEMAGNETICS.github.io", script)
            self.assertIn("/issues?state=all", script)
            self.assertIn("https://iambandobandz.com/network/board/", sitemap)

    def test_board_does_not_claim_final_account_backend(self) -> None:
        html = (ROOT / "network" / "board" / "index.html").read_text(encoding="utf-8")
        self.assertIn("No fake engagement", html)
        self.assertIn("no claim that this is the final account backend", html)
        self.assertIn("public GitHub data", html)


if __name__ == "__main__":
    unittest.main()
