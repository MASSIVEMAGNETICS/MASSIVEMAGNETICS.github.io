# Massive Magnetics Frontier Radar V1.2

Frontier Radar is a zero-paid-infrastructure public-source intelligence system for finding technically meaningful AI work before it becomes obvious.

## V1.2 architecture

```text
GitHub / Hugging Face / arXiv
        │
        ▼
allowlisted HTTPS client
(retries, response caps, redirect checks)
        │
        ▼
normalize + sanitize + deduplicate
        │
        ▼
history join against previous snapshot
        │
        ├── novelty
        ├── metric deltas
        └── velocity
        │
        ▼
V1.2 weighted ranker
        │
        ▼
observation hash + ranking hash
        │
        ▼
quality gate
(min items + healthy-source majority)
        │
   pass ─┴─ fail
    │        └── preserve last-known-good snapshot
    ▼
feed.json + feed.sha256 + status.json
    │
    ▼
Git commit → verified static Pages dashboard
```

## Score model

V1.2 scores each signal from 0–100:

- 28% frontier relevance
- 16% recency
- 12% traction
- 14% indie signal
- 14% reproducibility
- 8% novelty
- 8% observed velocity

`trend` is derived as `breakout`, `rising`, `new`, or `stable`.

This is a prioritization model, not a claim that a project is correct, safe, or genuinely novel.

## Integrity model

Every item has:

- `signal_id`: stable SHA-256 identity from source + external id
- `evidence_sha256`: hash of normalized upstream observation
- `ranking_sha256`: hash of the derived ranking decision
- `feed_sha256`: canonical snapshot hash
- `feed.sha256`: exact byte-level digest of `feed.json`
- `previous_snapshot_sha256`: pointer to the prior committed snapshot when available

The browser verifies the exact `feed.json` byte digest before rendering. A mismatch fails closed.

## Failure behavior

The scanner refuses to replace the current feed when:

- fewer than 12 validated signals survive,
- fewer than 2 sources meet the majority-success health threshold,
- feed or item integrity validation fails,
- upstream URLs violate the source allowlist.

The previous committed feed remains deployable.

## Collection scope

Public sources only:

- GitHub repository search
- Hugging Face public model metadata
- arXiv public Atom API

No private accounts, private repositories, authentication bypasses, personal inboxes, device telemetry, or covert collection.

## Run locally

Python 3.12+; standard library only.

```bash
python tools/frontier_radar.py
python tools/validate_frontier_feed.py frontier-radar/data/feed.json \
  --status frontier-radar/data/status.json
python -m unittest tests.test_frontier_radar -v
```

Set `GITHUB_TOKEN` for authenticated GitHub search limits. The token is never written to the feed.

## Refresh cadence

GitHub Actions refreshes the snapshot every six hours and on changes to the scanner/workflow. The refresh workflow has only `contents: write`; the Pages deployment workflow separately owns `pages: write` and `id-token: write`.

## Version

- Product: Frontier Radar
- Release: `1.2.0`
- Feed schema: `frontier-radar-feed/1.2`
- Score model: `frontier-radar-score/1.2`
