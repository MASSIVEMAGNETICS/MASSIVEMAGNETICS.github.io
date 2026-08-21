# Massive Magnetics Frontier Radar

A zero-paid-infrastructure public-signal intelligence radar for emerging AI research and indie engineering.

## Sources
- GitHub repository search
- Hugging Face model index
- arXiv Atom API

## Scoring
`score = 34% frontier relevance + 22% recency + 14% traction + 14% indie signal + 16% reproducibility`

Each normalized item carries a SHA-256 evidence hash. The complete feed also carries a SHA-256 digest. The scheduled GitHub Action refreshes the feed every six hours and deploys the sanitized Pages artifact.

## Local run
```bash
python tools/frontier_radar.py --output frontier-radar/data/feed.json
python -m unittest tests.test_frontier_radar -v
```

No third-party Python packages are required.
