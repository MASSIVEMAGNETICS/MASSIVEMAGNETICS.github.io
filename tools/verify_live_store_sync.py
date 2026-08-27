#!/usr/bin/env python3
"""Verify that deployed storefront projections agree with the canonical sync contract."""
from __future__ import annotations

import argparse
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "iambandobandz-sync-verifier/1.0"})
    with urlopen(request, timeout=20) as response:
        return response.read()


def get_json(base: str, path: str) -> dict:
    return json.loads(fetch(urljoin(base, path)).decode("utf-8"))


def verify(base: str) -> list[str]:
    errors: list[str] = []
    contract = get_json(base, "store/sync-contract.json")
    registry = get_json(base, "store/assets/assets.json")
    commerce = get_json(base, "store/commerce.json")
    html = fetch(urljoin(base, "store/")).decode("utf-8")

    if contract.get("schema_version") != "store-sync/1.0":
        errors.append("unsupported deployed store sync contract")
        return errors
    if commerce.get("status") != "active":
        errors.append("deployed commerce registry is not active")

    assets = {a.get("id"): a for a in registry.get("assets", [])}
    products = {p.get("sku"): p for p in registry.get("products", [])}
    contract_skus = {r.get("sku") for r in contract.get("releases", [])}
    if set(commerce.get("catalog_skus") or []) != contract_skus:
        errors.append("deployed commerce SKU set disagrees with sync contract")
    if set(products) != contract_skus:
        errors.append("deployed product SKU set disagrees with sync contract")

    storefront = registry.get("storefront") or {}
    if storefront.get("checkout_state") != commerce.get("status"):
        errors.append("deployed storefront checkout_state drift")
    if storefront.get("canonical_path") != commerce.get("canonical_path"):
        errors.append("deployed storefront canonical_path drift")

    for release in contract.get("releases", []):
        sku = release.get("sku")
        asset_id = release.get("art_asset")
        public_path = release.get("public_art_path")
        product = products.get(sku) or {}
        asset = assets.get(asset_id) or {}
        if product.get("art_asset") != asset_id:
            errors.append(f"{sku}: product art_asset drift")
        if product.get("checkout_state") != commerce.get("status"):
            errors.append(f"{sku}: product checkout_state drift")
        if asset.get("path") != public_path:
            errors.append(f"{sku}: registry artwork path drift")
        marker = f'data-sku="{sku}"'
        if marker not in html:
            errors.append(f"{sku}: missing rendered product card")
            continue
        start = html.index(marker)
        end = html.find("</article>", start)
        block = html[start:end if end >= 0 else len(html)]
        if f'src="{public_path}"' not in block:
            errors.append(f"{sku}: rendered artwork path drift")
        try:
            artwork = fetch(urljoin(base, public_path.lstrip("/")))
        except (HTTPError, URLError) as exc:
            errors.append(f"{sku}: artwork fetch failed: {exc}")
            continue
        if public_path.endswith(".svg"):
            if len(artwork) < 1000 or b"<svg" not in artwork:
                errors.append(f"{sku}: invalid SVG artwork")
        elif len(artwork) < 1000 or not artwork.startswith(b"RIFF") or artwork[8:12] != b"WEBP":
            errors.append(f"{sku}: invalid WEBP artwork")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--delay", type=float, default=5.0)
    args = parser.parse_args()
    base = args.base_url.rstrip("/") + "/"

    last_errors: list[str] = []
    for attempt in range(1, max(args.retries, 1) + 1):
        try:
            last_errors = verify(base)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_errors = [f"verification transport/parsing error: {exc}"]
        if not last_errors:
            print("Live store synchronization verified: contract, registry, commerce, rendering, and artwork agree.")
            return 0
        if attempt < args.retries:
            time.sleep(max(args.delay, 0))
    for error in last_errors:
        print(f"ERROR: {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
