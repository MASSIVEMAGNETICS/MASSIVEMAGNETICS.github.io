#!/usr/bin/env python3
"""Build the shippable static /bheardnetwork/ tree for GitHub Pages.

Source: the v2 board's static assets
    ~/workspace/goals/b-heard-network-platform-build/files/bheard-social-v2/board/static/
Dest:   <site-mm>/bheardnetwork/

What this script does (stdlib only, no network, no external tools):
  1. Copies the v2 static assets byte-identical, EXCEPT:
       - app.js: one documented path fix to the shared canonical
         asset "../assets/brand/b-heard-network.webp".
       - index.html: root-absolute asset paths -> relative paths, plus
         insertion of demo-data.js / bheard-api.js ahead of app.js and
         the demo banner. The B Heard Radio section comes from the v2
         source itself (single section — the build never inserts a
         second one).
  2. Generates demo-data.js from the SEED below (clearly-fake demo handles
     only, per DATA_CONTRACT section 5 — never the unverified "14,280+
     artists" style claims).
  3. Generates demo-media/<n>.wav — short synthesized sine tones so the
     player works with zero server. No real audio, no copyrighted material.
  4. Prints a SHA-256 manifest and verifies the copies against source.

It does NOT touch:
  - beheardnetwork/ (the misspelled redirect stub — wrong direction),
  - tools/build_site.py, tests/test_research_registry.py,
  - the v2 board source tree (read-only here; a sibling worker may be
    editing it — re-run this script to re-sync, it is idempotent).

Reproducible: run twice, the tree hashes are identical.

Usage:
    python3 tools/build_bheardnetwork.py [--source DIR] [--dest DIR]
    python3 tools/build_bheardnetwork.py --demo-assets-only [--dest DIR]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import struct
import sys
import wave
from pathlib import Path

DEFAULT_SOURCE = Path.home() / "workspace" / "goals" / "b-heard-network-platform-build" / "files" / "bheard-social-v2" / "board" / "static"
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEST = REPO_ROOT / "bheardnetwork"
BRAND_ASSET = REPO_ROOT / "assets" / "brand" / "b-heard-network.webp"
BRAND_ASSET_RELATIVE = "../assets/brand/b-heard-network.webp"

# Files copied byte-identical from the v2 board static tree. The logo is
# intentionally shared from assets/brand rather than duplicated here.
BYTE_IDENTICAL = ["style.css", "social-profiles.js", "social-feed.js",
                  "social-player.js", "social-radio.js"]

# ---------------------------------------------------------------------------
# Demo seed data. Handles are demo_* on purpose (DATA_CONTRACT section 5).
# Timestamps are fixed integer epoch seconds. Nothing here is real.
# ---------------------------------------------------------------------------
SEED = {
    "users": [
        {
            "id": 1, "handle": "demo_alice", "display": "Demo Alice",
            "email": "demo_alice@example.invalid",
            "bio": "Demo artist — sample data, not a real person.",
            "role": "artist", "plan": "free", "genre": "Hip-Hop",
            "location": "Demo City, OH", "website": "",
            "links": [{"label": "Demo link", "url": "https://example.invalid/demo"}],
            "theme": {"accent": "#e11d48", "background": "#09090c", "layout": "grid"},
            "avatar_url": None, "banner_url": None, "pinned_track_id": 1,
            "created": 1794200000,
        },
        {
            "id": 2, "handle": "demo_bob", "display": "Demo Bob",
            "email": "demo_bob@example.invalid",
            "bio": "Demo artist — sample data, not a real person.",
            "role": "artist", "plan": "free", "genre": "Rock",
            "location": "", "website": "",
            "links": [], "theme": {"accent": "#e11d48", "background": "#09090c", "layout": "grid"},
            "avatar_url": None, "banner_url": None, "pinned_track_id": None,
            "created": 1794203600,
        },
        {
            "id": 3, "handle": "demo_cleo", "display": "Demo Cleo",
            "email": "demo_cleo@example.invalid",
            "bio": "Demo artist — sample data, not a real person.",
            "role": "artist", "plan": "creator", "genre": "R&B",
            "location": "", "website": "",
            "links": [], "theme": {"accent": "#e11d48", "background": "#09090c", "layout": "grid"},
            "avatar_url": None, "banner_url": None, "pinned_track_id": None,
            "created": 1794207200,
        },
    ],
    "tracks": [
        {"id": 1, "user_id": 1, "title": "Demo Drop One", "genre": "Hip-Hop",
         "description": "Sample track — synthesized demo tone, not real audio.",
         "created": 1794210000, "votes": 5, "status": "published"},
        {"id": 2, "user_id": 1, "title": "Demo Drop Two", "genre": "Hip-Hop",
         "description": "Sample track — synthesized demo tone, not real audio.",
         "created": 1794213600, "votes": 2, "status": "published"},
        {"id": 3, "user_id": 2, "title": "Demo Rock Sketch", "genre": "Rock",
         "description": "Sample track — synthesized demo tone, not real audio.",
         "created": 1794217200, "votes": 3, "status": "published"},
        {"id": 4, "user_id": 3, "title": "Demo Slow Jam", "genre": "R&B",
         "description": "Sample track — synthesized demo tone, not real audio.",
         "created": 1794220800, "votes": 1, "status": "published"},
    ],
    "posts": [
        {"id": 1, "author_id": 1, "kind": "text",
         "body": "First demo post — this whole feed is sample data so the page works with no server.",
         "track_id": None, "created": 1794224400, "updated_at": 1794224400,
         "status": "published"},
        {"id": 2, "author_id": 2, "kind": "music",
         "body": "Demo music post — press play, it is a synthesized tone.",
         "track_id": 3, "created": 1794228000, "updated_at": 1794228000,
         "status": "published"},
        {"id": 3, "author_id": 3, "kind": "text",
         "body": "Demo post from Demo Cleo. Real posts appear once the live network is connected.",
         "track_id": None, "created": 1794231600, "updated_at": 1794231600,
         "status": "published"},
    ],
    "comments": [
        {"id": 1, "post_id": 1, "author_id": 2,
         "body": "Demo reply — sample comment.", "created": 1794225000,
         "status": "published"},
    ],
    "post_likes": [{"user_id": 2, "post_id": 1, "created": 1794224600}],
    "votes": [
        {"user_id": 2, "track_id": 1}, {"user_id": 3, "track_id": 1},
        {"user_id": 1, "track_id": 3}, {"user_id": 3, "track_id": 3},
        {"user_id": 1, "track_id": 4},
    ],
    "follows": [{"follower": 2, "followed": 1}, {"follower": 3, "followed": 1},
                {"follower": 1, "followed": 2}],
}

# One synthesized tone per demo track id (Hz). 3 s each, 22050 Hz mono 16-bit.
DEMO_TONES = {1: 220.00, 2: 277.18, 3: 329.63, 4: 440.00}
TONE_SECONDS = 3
TONE_RATE = 22050

BANNER_HTML = """<div id="bheard-banner" role="status"><strong id="bheard-mode">DEMO MODE</strong> — <span id="bheard-mode-text">Sample artists, tracks and posts. Nothing here is real — this is demo data so the page works with no server. Try it: sign in as demo_alice@example.invalid with any password (demo sign-in is local-only).</span> <details id="bheard-connect"><summary>Connect to the live network</summary><form id="bheard-connect-form"><label>Live network address (your current tunnel URL)<input id="bheard-api-input" name="apiBase" type="url" placeholder="https://your-tunnel.trycloudflare.com" autocomplete="off"></label><button class="primary" type="submit">Connect</button><button id="bheard-demo-btn" class="outline" type="button">Use demo data</button><p id="bheard-connect-status" role="status"></p></form></details></div>"""

BANNER_CSS = """<style>#bheard-banner{background:#3a0d16;border-bottom:2px solid #d20e2f;color:#ffd7de;font-size:13px;line-height:1.5;padding:10px clamp(18px,4vw,64px)}#bheard-banner.live{background:#0d2b16;border-bottom-color:#22c55e;color:#d1fae0}#bheard-banner summary{cursor:pointer;display:inline-block;font-weight:700;margin-left:10px}#bheard-banner form{display:grid;gap:8px;margin-top:10px;max-width:560px}#bheard-banner input{width:100%}</style>"""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"index.html transform {label}: expected 1 occurrence of {old!r}, found {count}")
    return text.replace(old, new, 1)


def replace_n(text: str, old: str, new: str, expected: int, label: str) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"index.html transform {label}: expected {expected} occurrences of {old!r}, found {count}")
    return text.replace(old, new)


def build_index(source: Path) -> str:
    html = (source / "index.html").read_text(encoding="utf-8")
    # Root-absolute asset paths -> paths relative to /bheardnetwork/.
    html = replace_once(html, 'href="/style.css"', 'href="style.css"', "stylesheet")
    html = replace_once(
        html, '<script src="/app.js" defer></script>',
        '<script src="demo-data.js" defer></script>'
        '<script src="bheard-api.js" defer></script>'
        '<script src="app.js" defer></script>',
        "app script (shim loads first)",
    )
    for name in ("social-profiles", "social-feed", "social-player", "social-radio"):
        html = replace_once(html, f'src="/{name}.js"', f'src="{name}.js"', f"{name} script")
    html = replace_n(html, 'src="/logo.jpg"',
                      f'src="{BRAND_ASSET_RELATIVE}"', 3, "shared logo images")
    # Demo banner + its CSS, right after <body> / in <head>.
    html = replace_once(html, "<body>", "<body>" + BANNER_HTML, "demo banner")
    html = replace_once(html, "</head>", BANNER_CSS + "</head>", "banner css")
    # The radio section comes from the v2 source (single section). If it
    # ever disappears upstream, fail loudly instead of shipping a page
    # with no radio or a duplicate one.
    if 'id="radio"' not in html:
        raise RuntimeError("index.html transform radio section: v2 source has no id=\"radio\" section")
    if 'id="bheard-radio"' in html:
        raise RuntimeError("index.html transform radio section: duplicate bheard-radio section present")
    return html


def write_tone(path: Path, freq: float) -> None:
    frames = int(TONE_RATE * TONE_SECONDS)
    samples = bytearray()
    for i in range(frames):
        t = i / TONE_RATE
        env = min(1.0, i / (TONE_RATE * 0.05)) * min(1.0, (frames - i) / (TONE_RATE * 0.3))
        value = 0.5 * math.sin(2 * math.pi * freq * t) + 0.15 * math.sin(2 * math.pi * freq * 2 * t)
        samples += struct.pack("<h", int(12000 * env * value))
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(TONE_RATE)
        wav.writeframes(bytes(samples))



def build_demo_assets(dest: Path) -> list[tuple[str, str, int]]:
    """Generate the demo seed and synthetic audio without the private v2 source tree."""
    dest = Path(dest).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    manifest: list[tuple[str, str, int]] = []

    def record(path: Path) -> None:
        rel = str(path.relative_to(dest))
        manifest.append((rel, sha256_file(path), path.stat().st_size))

    demo_js = dest / "demo-data.js"
    demo_js.write_text(
        "'use strict';\\n"
        "/* B Heard Network demo seed data — GENERATED by tools/build_bheardnetwork.py.\\n"
        " * Sample artists/tracks/posts only. Nothing here is real. Handles are\\n"
        " * demo_* on purpose (DATA_CONTRACT section 5). Do not hand-edit: change\\n"
        " * the SEED in the build script and re-run it. */\\n"
        "window.BHEARD_DEMO = "
        + json.dumps(SEED, indent=2, ensure_ascii=False)
        + ";\\n",
        encoding="utf-8",
    )
    record(demo_js)

    media_dir = dest / "demo-media"
    media_dir.mkdir(parents=True, exist_ok=True)
    for track_id, freq in sorted(DEMO_TONES.items()):
        tone = media_dir / f"{track_id}.wav"
        write_tone(tone, freq)
        record(tone)
    return manifest


def build(source: Path, dest: Path) -> list[tuple[str, str, int]]:
    if not source.is_dir():
        raise FileNotFoundError(f"v2 static source dir missing: {source}")
    if not BRAND_ASSET.is_file() or BRAND_ASSET.stat().st_size == 0:
        raise FileNotFoundError(f"shared B Heard brand asset missing: {BRAND_ASSET}")
    dest = Path(dest).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    manifest: list[tuple[str, str, int]] = []

    def record(path: Path) -> None:
        rel = str(path.relative_to(dest))
        manifest.append((rel, sha256_file(path), path.stat().st_size))

    # 1. Byte-identical copies.
    for name in BYTE_IDENTICAL:
        src = source / name
        if not src.exists():
            raise FileNotFoundError(f"v2 static source missing: {src}")
        dst = dest / name
        shutil.copy2(src, dst)
        if sha256_file(dst) != sha256_file(src):
            raise RuntimeError(f"copy verification failed: {name}")
        record(dst)

    # 2. app.js — one documented path fix only.
    app_src = (source / "app.js").read_text(encoding="utf-8")
    if app_src.count('"/logo.jpg"') != 1:
        raise RuntimeError(f"app.js transform: expected 1 occurrence of \"/logo.jpg\", found {app_src.count(chr(34) + '/logo.jpg' + chr(34))}")
    app_dst = dest / "app.js"
    app_dst.write_text(
        app_src.replace('"/logo.jpg"', f'"{BRAND_ASSET_RELATIVE}"'),
        encoding="utf-8",
    )
    record(app_dst)

    # 3. index.html — relative paths + banner (radio section comes from
    # the v2 source; see build_index).
    index_dst = dest / "index.html"
    index_dst.write_text(build_index(source), encoding="utf-8")
    record(index_dst)

    # 4. Demo seed and tones use the same helper as CI and site builds.
    manifest.extend(build_demo_assets(dest))

    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument(
        "--demo-assets-only",
        action="store_true",
        help="Generate the deterministic demo seed and tones without the private v2 source tree.",
    )
    args = parser.parse_args(argv)
    if args.demo_assets_only:
        manifest = build_demo_assets(args.dest)
        print(f"Built B Heard demo assets in {args.dest}")
    else:
        manifest = build(args.source, args.dest)
        print(f"Built {args.dest} from {args.source}")
    for rel, digest, size in sorted(manifest):
        print(f"  {digest}  {size:7d}  {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
