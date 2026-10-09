"""Read-only source audit for B Heard Network production readiness.

This script never treats a configured payment link as proof of a successful payment
or a deployed page as proof of a working backend.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


def audit(root: Path = ROOT) -> dict[str, str]:
    def read(path: str) -> str:
        file = root / path
        return file.read_text(encoding="utf-8") if file.is_file() else ""

    home = read("network/index.html")
    board = read("network/board/index.html")
    board_js = read("network/board/board.js")
    thanks = read("network/thanks/index.html")
    raw_offer = read("network/offer.json")
    try:
        offer = json.loads(raw_offer)
    except (ValueError, TypeError):
        offer = {}

    checkout_url = str((offer.get("stripe") or {}).get("checkout_url") or "")
    checkout_host = urlparse(checkout_url).hostname
    canonical_host = urlparse(str(offer.get("canonical_path") or "")).hostname
    return {
        "frontend_source": "CANDIDATE" if "<main" in home else "BLOCKED",
        "mobile_viewport_source": "CANDIDATE" if 'name="viewport"' in home else "BLOCKED",
        "independent_origin": "BLOCKED" if canonical_host == "iambandobandz.com" else (
            "CANDIDATE" if canonical_host else "UNKNOWN"
        ),
        "canonical_logo_source": "CANDIDATE" if 'data-bheard-canonical-logo' in home else "BLOCKED",
        "board_identity": "GITHUB_ALPHA" if "api.github.com" in board_js and "GitHub account" in board else "UNKNOWN",
        "stripe_link_source": "CANDIDATE" if checkout_host == "buy.stripe.com" and offer.get("price_cents") == 999 else "BLOCKED",
        "stripe_payment_verified": "UNKNOWN",
        "webhook_and_order_intake": "UNKNOWN",
        "fulfillment": "UNKNOWN",
        "first_party_auth": "UNKNOWN",
        "database_and_audio_storage": "UNKNOWN",
        "anti_fraud_voting": "UNKNOWN",
        "remote_analytics_collector": "CANDIDATE" if 'name="iambandobandz:analytics-endpoint"' in home else "BLOCKED",
        "checkout_return_proof_safe": "CANDIDATE" if "checkout_return_unverified" in thanks else "BLOCKED",
        "live_dns_tls_uptime": "UNKNOWN",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--strict", action="store_true", help="Exit 1 unless every gate is verified")
    args = parser.parse_args()
    findings = audit(args.root)
    print(json.dumps({"schema": "bheard-source-readiness-v1", "findings": findings}, sort_keys=True, indent=2))
    return int(args.strict and any(value != "VERIFIED_LIVE" for value in findings.values()))


if __name__ == "__main__":
    raise SystemExit(main())
