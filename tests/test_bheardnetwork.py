"""Tests for the shippable static /bheardnetwork/ tree (GitHub Pages).

The tree is built by tools/build_bheardnetwork.py from the v2 board's
static assets plus two hand-written files (bheard-api.js, the live/demo
API shim) and generated demo data/tones. These tests assert on the
committed tree only, so they run the same in CI (where the v2 source
dir does not exist) as locally. The source-sync checks skip when the
v2 source dir is absent.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BH = ROOT / "bheardnetwork"
V2_STATIC = (
    Path.home() / "workspace" / "goals" / "b-heard-network-platform-build"
    / "files" / "bheard-social-v2" / "board" / "static"
)
BUILD_SCRIPT = ROOT / "tools" / "build_bheardnetwork.py"
DEMO_CHECK = ROOT / "tests" / "bheardnetwork_demo_check.js"

# Files the build produces (copied / transformed / generated).
BUILT_FILES = [
    "index.html", "style.css", "app.js", "social-profiles.js",
    "social-feed.js", "social-player.js", "logo.jpg", "demo-data.js",
    "demo-media/1.wav", "demo-media/2.wav", "demo-media/3.wav",
    "demo-media/4.wav",
]
# Hand-written files that live in the tree alongside the build output.
HANDWRITTEN_FILES = ["bheard-api.js", "BUILD_EVIDENCE.md"]

# Files copied byte-identical from the v2 board static tree.
BYTE_IDENTICAL = ["style.css", "social-profiles.js", "social-feed.js",
                  "social-player.js", "logo.jpg"]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestBheardNetworkTree(unittest.TestCase):
    def test_tree_files_exist(self) -> None:
        for name in BUILT_FILES + HANDWRITTEN_FILES:
            self.assertTrue((BH / name).is_file(), f"missing bheardnetwork/{name}")

    def test_index_uses_relative_asset_paths(self) -> None:
        html = (BH / "index.html").read_text(encoding="utf-8")
        for bad in ('"/style.css"', '"/app.js"', '"/logo.jpg"',
                    '"/social-profiles.js"', '"/social-feed.js"',
                    '"/social-player.js"'):
            self.assertNotIn(bad, html, f"root-absolute asset ref remains: {bad}")
        for good in ('href="style.css"', 'src="app.js"', 'src="logo.jpg"',
                     'src="social-profiles.js"', 'src="social-feed.js"',
                     'src="social-player.js"'):
            self.assertIn(good, html, f"relative asset ref missing: {good}")

    def test_index_script_order_and_no_inline_code(self) -> None:
        html = (BH / "index.html").read_text(encoding="utf-8")
        order = [html.index(s) for s in
                 ('src="demo-data.js"', 'src="bheard-api.js"', 'src="app.js"')]
        self.assertEqual(order, sorted(order),
                         "shim must load before app.js (demo-data, bheard-api, app)")
        self.assertNotIn("<script>", html, "inline <script> block present")
        self.assertNotRegex(html, r"\son\w+\s*=", "inline event handler present")

    def test_index_has_demo_banner_and_radio(self) -> None:
        html = (BH / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="bheard-banner"', html)
        self.assertIn("DEMO MODE", html)
        self.assertIn("demo_alice@example.invalid", html)
        # Exactly ONE radio section: the real one from the v2 source.
        # (Coordinator merge 2026-11-10: the build used to insert a second
        # demo-only #bheard-radio section; that duplicate is gone.)
        self.assertIn('id="radio"', html)
        self.assertIn('id="radio-play"', html)
        self.assertNotIn('id="bheard-radio"', html)
        self.assertNotIn('id="bheard-radio-play"', html)
        self.assertIn('id="bheard-connect-form"', html)

    def test_all_local_script_and_style_refs_exist(self) -> None:
        # A dangling <script src> shipped once (social-radio.js referenced
        # but not copied); every relative local asset ref must resolve.
        html = (BH / "index.html").read_text(encoding="utf-8")
        refs = re.findall(r'(?:src|href)="([^":]+)"', html)
        self.assertTrue(refs, "no local asset refs found at all")
        for ref in refs:
            if ref.startswith(("http", "#", "data:")):
                continue
            target = BH / ref
            self.assertTrue(target.is_file(), f"referenced asset missing: {ref}")
        self.assertIn('src="social-radio.js"', html)

    def test_no_hardcoded_tunnel_url(self) -> None:
        for path in sorted(BH.rglob("*")):
            if not path.is_file() or path.suffix not in (".js", ".html", ".md"):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            hosts = re.findall(r"[a-z0-9-]+\.trycloudflare\.com", text)
            for host in hosts:
                self.assertEqual(host, "your-tunnel.trycloudflare.com",
                                 f"hardcoded tunnel host in {path}: {host}")
            self.assertNotRegex(text, r"100\.\d+\.\d+\.\d+",
                                f"hardcoded Tailscale IP in {path}")
            self.assertNotIn("ngrok", text, f"ngrok reference in {path}")
            self.assertNotIn(".ts.net", text, f"Tailscale hostname in {path}")

    def test_no_unverified_audience_claims(self) -> None:
        text = (BH / "demo-data.js").read_text(encoding="utf-8")
        for bad in ("14,280", "14280", "842K", "842,"):
            self.assertNotIn(bad, text, "unverified audience claim in demo data")
        self.assertIn("demo_alice", text)

    def test_demo_data_handles_are_clearly_fake(self) -> None:
        text = (BH / "demo-data.js").read_text(encoding="utf-8")
        payload = text.split("window.BHEARD_DEMO =", 1)[1].rstrip().rstrip(";")
        seed = json.loads(payload)
        handles = [u["handle"] for u in seed["users"]]
        self.assertTrue(handles, "demo seed has no users")
        for handle in handles:
            self.assertTrue(handle.startswith("demo_"),
                            f"demo handle not clearly fake: {handle}")
        self.assertIn("demo_alice@example.invalid",
                      [u["email"] for u in seed["users"]])

    def test_demo_tones_are_valid_wavs(self) -> None:
        for n in (1, 2, 3, 4):
            with wave.open(str(BH / "demo-media" / f"{n}.wav"), "rb") as wav:
                self.assertEqual(wav.getnchannels(), 1)
                self.assertEqual(wav.getsampwidth(), 2)
                self.assertEqual(wav.getframerate(), 22050)
                self.assertEqual(wav.getnframes(), 3 * 22050)

    def test_copied_js_has_no_new_external_urls(self) -> None:
        for name in ("app.js", "social-profiles.js", "social-feed.js",
                     "social-player.js"):
            text = (BH / name).read_text(encoding="utf-8")
            urls = sorted(set(re.findall(r"https://[^\s\"'<>]+", text)))
            for url in urls:
                self.assertTrue(
                    url.startswith("https://accounts.google.com/gsi/client"),
                    f"unexpected external URL in {name}: {url}",
                )

    def test_app_js_only_documented_change(self) -> None:
        text = (BH / "app.js").read_text(encoding="utf-8")
        self.assertNotIn('"/logo.jpg"', text)
        self.assertEqual(text.count('"logo.jpg"'), 1)

    @unittest.skipIf(not shutil.which("node"), "node not available")
    def test_js_syntax(self) -> None:
        for js in sorted(BH.glob("*.js")):
            proc = subprocess.run(["node", "--check", str(js)],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0,
                             f"node --check failed for {js.name}: {proc.stderr}")

    @unittest.skipIf(not shutil.which("node"), "node not available")
    def test_demo_store_end_to_end(self) -> None:
        proc = subprocess.run(["node", str(DEMO_CHECK)],
                              capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(proc.returncode, 0,
                         f"demo-store harness failed:\n{proc.stdout}\n{proc.stderr}")
        self.assertIn("All demo-store checks passed.", proc.stdout)

    def test_misspelled_redirect_stub_untouched(self) -> None:
        stub = ROOT / "beheardnetwork" / "index.html"
        self.assertTrue(stub.is_file(), "misspelled redirect stub is gone")
        text = stub.read_text(encoding="utf-8")
        self.assertIn('location.replace("/network/")', text)
        self.assertIn('rel="canonical" href="https://iambandobandz.com/network/"', text)
        self.assertLess(len(text), 1000, "redirect stub grew unexpectedly")
        self.assertNotIn("bheard-api", text)
        self.assertNotIn("demo", text.lower())


@unittest.skipIf(not V2_STATIC.is_dir(), "v2 board static source not present")
class TestBheardNetworkSourceSync(unittest.TestCase):
    """Only runs where the v2 board tree exists (this VM, not CI)."""

    def test_byte_identical_copies_match_source(self) -> None:
        for name in BYTE_IDENTICAL:
            self.assertEqual(sha256_file(BH / name),
                             sha256_file(V2_STATIC / name),
                             f"bheardnetwork/{name} drifted from v2 source")

    def test_app_js_matches_source_plus_one_path_fix(self) -> None:
        source = (V2_STATIC / "app.js").read_text(encoding="utf-8")
        built = (BH / "app.js").read_text(encoding="utf-8")
        self.assertEqual(built, source.replace('"/logo.jpg"', '"logo.jpg"'))

    def test_build_reproduces_committed_tree(self) -> None:
        sys.path.insert(0, str(ROOT / "tools"))
        import build_bheardnetwork
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "bheardnetwork"
            manifest = build_bheardnetwork.build(V2_STATIC, dest)
            for rel, digest, _size in manifest:
                self.assertTrue((dest / rel).is_file(), f"rebuild missing {rel}")
                self.assertEqual(sha256_file(BH / rel), digest,
                                 f"committed bheardnetwork/{rel} != rebuild")
            # Rebuild is deterministic: run again, hashes must not move.
            manifest2 = build_bheardnetwork.build(V2_STATIC, dest)
            self.assertEqual([m[1] for m in sorted(manifest)],
                             [m[1] for m in sorted(manifest2)])


if __name__ == "__main__":
    unittest.main()
