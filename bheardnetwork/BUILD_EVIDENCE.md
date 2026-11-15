# B Heard Network — static /bheardnetwork/ build evidence

Built 2026-11-10 by the STATIC PAGES slice (subagent) from the v2 board's
static assets. Full authorization from Bando 2026-11-10; $0 budget, no
spend, no signups, no credentials, no deletions, no push/commit by this
worker.

## Verdict

SHIPPABLE as a static demo that defaults to local-only demo data. The
sanitized Pages builder already includes both `assets/` and
`bheardnetwork/` in its copy list. Live mode from the Pages origin
still requires CORS and credential support on the Dell API.

## What it is

`bheardnetwork/` in this repo = the B Heard social platform (profiles,
feed, player, radio) as a static site for GitHub Pages. It works with
NO server (demo data, clearly labeled DEMO MODE) and lights up against
the live Dell API when the tunnel is live.

- **Demo mode (default):** seed artists/tracks/posts (`demo_alice`,
  `demo_bob`, `demo_cleo`), synthesized tone audio, local-only sign-in
  (`demo_alice@example.invalid`, any password). Votes, follows, posts,
  comments, uploads, profile edits and hide/unhide all work against an
  in-memory demo store. Nothing leaves the browser.
- **Live mode:** the shim probes, in order, `?api=<url>`, localStorage
  `bheard.apiBase`, then same-origin `/api/config`. First base that
  answers JSON wins. No tunnel URL is hardcoded anywhere — tunnel URLs
  rotate; the owner pastes the current one into the banner form and it
  lives only in localStorage. If no base answers, the page falls back
  to demo data.
- **Radio:** demo mode plays the sample tracks as a playlist; live mode
  plays `config.radio_url` when the Dell publishes one, otherwise it
  says the stream engine is still in progress. No stream URL invented.

## Files

Build: `python3 tools/build_bheardnetwork.py` (stdlib only, idempotent,
reproducible — run twice, same hashes). It copies the v2 board static
assets, applies the documented path transforms, reuses the canonical
site brand asset, and generates the demo seed + tones. The
`--demo-assets-only` mode generates the seed and tones without the
private sibling v2 source tree.

| File | Origin |
| --- | --- |
| `index.html` | v2 `index.html` + relative asset paths + demo banner + radio section + shim scripts first |
| `style.css`, `social-profiles.js`, `social-feed.js`, `social-player.js`, `social-radio.js` | v2 board static, byte-identical |
| `assets/brand/b-heard-network.webp` | Shared canonical site brand asset; reused by relative path instead of duplicating a logo binary |
| `app.js` | v2 `app.js` with ONE fallback path change: `"/logo.jpg"` → `"../assets/brand/b-heard-network.webp"` |
| `bheard-api.js` | hand-written shim: detection, fetch/media patching, demo store, radio |
| `demo-data.js` | generated from the seed in the build script (demo_* handles only) |
| `demo-media/1–4.wav` | generated 3 s sine tones (220/277.18/329.63/440 Hz), no real audio |
| `BUILD_EVIDENCE.md` | this file |

Source hashes (v2 board static) — initial at copy time, final at
re-sync: `app.js` and `index.html` changed mid-build (sibling audit
worker, 2026-11-10 ~19:13–19:16 ET); `social-player.js` changed once
(added Hide/Unhide track visibility). Final source hashes are recorded
in the parent report; the committed tree matches the final sources
(`tests/test_bheardnetwork.py::TestBheardNetworkSourceSync` enforces it
where the source tree exists).

## Tests

- `python3 -m unittest tests.test_bheardnetwork -v` — validates tree
  contents, shared brand path, script order, no inline code, no
  hardcoded tunnel URL/IP, no unverified audience claims, clearly fake
  demo handles, deterministic demo asset generation, valid WAV metadata,
  no new external URLs, app.js source transform, `node --check` on JS,
  and the demo-store end-to-end harness (`tests/bheardnetwork_demo_check.js`, 41 checks: sign-in,
  feed, profiles, discography, posts, likes, comments, votes, follows,
  upload, hide/unhide, checkout blocked, media, logout), misspelled
  redirect stub untouched, source-sync + rebuild reproducibility.
- Full site suite: `python3 -m unittest discover -s tests` — see parent
  report for the final count (baseline before this work: 57 tests OK).

## Preserved (untouched)

- `beheardnetwork/index.html` — misspelled folder, 698-byte redirect
  stub to `/network/` (renaming it would put the redirect live — the
  wrong direction).
- `tools/build_site.py`, `tests/test_research_registry.py` — the 3
  already-modified files stay exactly as found; verified with
  `git status --short` before and after.

## Blockers / follow-ups (parent's call)

1. **Deploy gap:** Pages publishes `_site/` built by
   `tools/build_site.py`, whose COPY_ITEMS lists only the misspelled
   `beheardnetwork`. This new `bheardnetwork/` folder will NOT be
   published until someone adds `"bheardnetwork",` to COPY_ITEMS.
   This worker was forbidden from touching `build_site.py`.
2. **Live CORS:** from the Pages origin, live mode needs the Dell API
   to send CORS headers for the Pages origin (and credential support
   for sign-in sessions). Until then, live mode works when this tree
   is served same-origin by the Dell/tunnel; otherwise it falls back
   to demo data by design.
3. **Visibility endpoint (live):** the audit worker added Hide/Unhide
   (`POST /api/track/<id>/visibility`) to the v2 player UI; the demo
   store implements it, but the live route depends on the coordinator
   wiring it on the Dell.
4. **No post-report UI in v2** (known contract gap, §3.2) — unchanged.

## Coordinator addendum (2026-11-10 ~19:30 ET, verified by coordinator)

- Re-ran everything: site suite 73 tests with **1 failure** —
  `test_build_reproduces_committed_tree` (committed index.html 4063a0ff…
  vs rebuild 01978051…); new `test_bheardnetwork` 16 tests, same single
  failure; demo harness **41/41 pass**. The failure is the drift detector
  working as designed, NOT a broken build: the sibling radio slice has
  since added `social-radio.js` + a radio section to the v2 board tree
  (after this slice's final sync). All other tests pass.
- Shim hash (fills the manifest gap noted above): `bheard-api.js`
  SHA-256 `0cb43e89fc74e2b37186a8b63c385bd194e2fb4c4c7d412228c186dda07cca4f`.
  Staged `app.js` 7bb612ba… and `index.html` 4063a0ff… match the manifest.
- **CORRECTION — blocker #1 (COPY_ITEMS) is wrong.** Verified
  programmatically: `COPY_ITEMS` in the working tree contains BOTH
  `"beheardnetwork"` (misspelled) AND `"bheardnetwork"` (correct) — the
  correct spelling was added in the pre-existing uncommitted modification
  of `tools/build_site.py` (see `git diff`: `+ "bheardnetwork",`). No edit
  needed; the prepared push WILL publish the new folder.
- **Pending final integration (after the radio slice lands):** re-run
  `python3 tools/build_bheardnetwork.py` into the committed tree. The
  build script's fixed lists do not yet include the radio assets — add
  `"social-radio.js"` to `BYTE_IDENTICAL` and `"social-radio"` to the
  src-relativization loop (line 174) first, or the rebuilt index.html will
  reference `/social-radio.js` root-absolute with no file present. Then
  re-run the full site suite + harness; the drift test must go green.
- Blockers #2 (live CORS — demo fallback covers it) and #4 (post-report UI
  gap) stand as reported. Blocker #3 is a Dell-deploy step, not a code gap:
  the visibility route already exists in the v2 tree (`server.py:575`).
- No push, no commit run by the coordinator. No GPT needed.

## Coordinator integration addendum (2026-11-10 ~19:45 ET, verified by coordinator)

Single-radio merge — the staged page used to ship TWO "B HEARD RADIO"
sections (the real `#radio` from the v2 source + a demo-only
`#bheard-radio` inserted by this build) and a dangling
`<script src="/social-radio.js">` (referenced, never copied). Fixed:
- `tools/build_bheardnetwork.py`: `social-radio.js` added to
  BYTE_IDENTICAL and to the src-relativization loop; the duplicate
  `#bheard-radio` insertion REMOVED (the build now fails loudly if the
  v2 source ever loses its `id="radio"` section); dead `#bheard-radio`
  CSS removed; docstring updated.
- `bheardnetwork/bheard-api.js` (hand-written shim, not a build output):
  demo store now answers `GET /api/radio/now` + `/api/radio/stats`
  with the board's shapes, so the single section works in demo mode
  (sample playlist, looping, `ended` handler advances it); the src
  patch maps `/radio/stream` to the live base in live mode and to the
  current demo tone in demo mode, and sets/clears the
  `audio.dataset.radioStream` marker the radio script relies on.
  SHA-256 (post-merge): `0a8c7138baa1310d95b1ed043b34fe54a03991ba1a74d3c44bcaef400b7aa810`.
- `board/static/social-radio.js` (v2 tree): the track-play listener now
  also accepts the shim's `dataset.radioStream` marker, so a resolved
  radio src is never mistaken for a track play on the static copy.
  SHA-256 (v2 + staged, identical): `0b70ee0883952c1625eb5f14f1e3f9506bbfa7e04bd95c11ecf29bed695c0ee6`.
- Tests updated: `test_index_has_demo_banner_and_radio` now asserts
  exactly one radio section (`id="radio"`, no `id="bheard-radio"`);
  new `test_all_local_script_and_style_refs_exist` (would have caught
  the dangling script); harness gained 8 radio checks (now/stats API +
  src-patch mapping + marker set/clear via a FakeMedia stub).
- Verified by coordinator after the merge: site suite **74/74 OK**,
  demo harness **49/49 checks pass**, `node --check` clean on all 7
  staged JS files, board suite **134/134 OK**, HTTP smoke 6/6 files 200
  (incl. social-radio.js). Rebuilt tree hash: index.html
  `572ee0e8a6d47fd0d9187ca0265964a18de25d9720116480795cdb1ba646c0f2`.
- COPY_ITEMS correction (restated): blocker #1 in the worker report was
  wrong — `COPY_ITEMS` already contains `"bheardnetwork"` in the
  working tree (pre-existing uncommitted edit); the prepared push WILL
  publish the folder. No edit made.
- Known demo-only divergence, left alone: the demo store's feed still
  ranks by votes when `sort=top` is requested (the harness enshrines
  it), while the live server is chronological-only. The staged UI can
  no longer request `sort=top` (option removed), so the branch is
  unreachable in practice.
- Live note: radio playback from Pages uses plain `<audio>` against
  `<apiBase>/radio/stream`, which does not need CORS for playback;
  API calls (sign-in, feed, radio/now) still need the tunnel + CORS
  as previously flagged.
- No push, no commit run. No GPT needed.


## 2026-11-14 — deterministic demo asset completion

The 2026-11-15 main-branch text-only build commit explicitly deferred
binary assets. Exact-head Site Contract CI and Canonical Registry CI on
B Heard order-intake PR #57 then failed because `bheardnetwork/logo.jpg`
and `bheardnetwork/demo-media/*.wav` were absent. The registry count
assertion itself passed; the earlier 14-versus-13 note is stale.

This bounded correction:
- reuses the existing canonical `assets/brand/b-heard-network.webp`
  (Git blob `39aa923709fa059b42122743abbff2bf1112f620`) instead of
  inventing or duplicating a logo binary;
- updates the three HTML logo references and the app-card fallback to
  the shared relative asset path;
- extracts deterministic demo-data/WAV generation into
  `build_demo_assets()` and adds `--demo-assets-only`, which does not
  require the private v2 source directory;
- makes `tools/build_site.py` materialize those generated assets before
  copying the static tree;
- makes the tests generate the same assets before asserting their
  contents and checks repeat-generation hashes plus sanitized-site
  asset resolution;
- ignores generated `bheardnetwork/demo-media/` so local tests do not
  leave untracked binary files.

No deployment workflow, Pages setting, domain, DNS, credential, secret,
payment, webhook, or production state was changed. The live API remains
a separate unverified integration boundary.

Verification status at commit time: pending exact-head GitHub Actions.
