#!/usr/bin/env python3
"""Zero-dependency integrity gate for the IAMBANDOBANDZ direct store."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "store"
REGISTRY_PATH = STORE / "assets" / "assets.json"
EXPECTED_CNAME = "iambandobandz.com"
REQUIRED_SKUS = {
    "IBB-OMS-2026",
    "IBB-GEN-2026",
    "IBB-EV-2026",
    "IBB-SC-2026",
    "IBB-NLTG-2026",
    "IBB-CB-DLX-2025",
}


def fail(message: str) -> None:
    raise SystemExit(f"STORE VALIDATION FAILED: {message}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def local_asset_path(web_path: str) -> Path:
    prefix = "/store/"
    if not isinstance(web_path, str) or not web_path.startswith(prefix):
        fail(f"asset path must be rooted under {prefix}: {web_path!r}")
    candidate = ROOT / web_path.lstrip("/")
    try:
        candidate.resolve().relative_to(STORE.resolve())
    except ValueError:
        fail(f"asset escapes store root: {web_path}")
    return candidate


def validate_registry() -> None:
    if not REGISTRY_PATH.is_file():
        fail("assets.json is missing")
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if data.get("schema_version") != "1.0.0":
        fail("unsupported schema_version")

    storefront = data.get("storefront") or {}
    if storefront.get("payment_urls_fabricated") is not False:
        fail("payment_urls_fabricated must remain false")
    if storefront.get("dns_state") != "not_changed_by_this_branch":
        fail("store branch may not claim a DNS change")

    assets = data.get("assets")
    if not isinstance(assets, list) or not assets:
        fail("assets must be a non-empty list")
    ids: set[str] = set()
    for asset in assets:
        asset_id = asset.get("id")
        if not asset_id or asset_id in ids:
            fail(f"missing or duplicate asset id: {asset_id!r}")
        ids.add(asset_id)
        path = local_asset_path(asset.get("path"))
        if not path.is_file():
            fail(f"registered asset is missing: {path.relative_to(ROOT)}")
        expected_hash = ((asset.get("derived") or {}).get("sha256") or "").lower()
        actual_hash = sha256(path)
        if expected_hash != actual_hash:
            fail(f"SHA-256 mismatch for {path.relative_to(ROOT)}: {actual_hash}")

    products = data.get("products")
    if not isinstance(products, list):
        fail("products must be a list")
    product_skus = [p.get("sku") for p in products]
    if len(product_skus) != len(set(product_skus)):
        fail("product SKUs must be unique")
    if set(product_skus) != REQUIRED_SKUS:
        fail(f"catalog SKU set drifted: {sorted(product_skus)}")

    html = (STORE / "index.html").read_text(encoding="utf-8")
    for product in products:
        sku = product["sku"]
        if f'data-sku="{sku}"' not in html:
            fail(f"product {sku} is absent from store/index.html")
        if product.get("art_asset") not in ids:
            fail(f"product {sku} references unknown art asset")

        state = product.get("checkout_state")
        checkout_url = product.get("checkout_url")
        if state == "active":
            parsed = urlparse(checkout_url or "")
            if parsed.scheme != "https" or not parsed.netloc:
                fail(f"active checkout for {sku} must be an absolute HTTPS URL")
        elif checkout_url is not None:
            fail(f"inactive checkout for {sku} must not expose a URL")


def validate_site_boundary() -> None:
    for relative in ("store/index.html", "store/styles.css", "store/store.js"):
        if not (ROOT / relative).is_file():
            fail(f"required storefront file missing: {relative}")
    cname = (ROOT / "CNAME").read_text(encoding="utf-8").strip()
    if cname != EXPECTED_CNAME:
        fail(f"CNAME boundary changed unexpectedly: {cname!r}")


def main() -> int:
    validate_site_boundary()
    validate_registry()
    print("Store validation passed: assets, hashes, SKUs, checkout boundary, and CNAME are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
