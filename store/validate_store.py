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
COMMERCE_PATH = STORE / "commerce.json"
EXPECTED_CNAME = "iambandobandz.com"
REQUIRED_SKUS = {
    "IBB-OMS-2026",
    "IBB-GEN-2026",
    "IBB-EV-2026",
    "IBB-SC-2026",
    "IBB-NLTG-2026",
    "IBB-CB-DLX-2025",
}
REQUIRED_FORMATS = {"digital", "cd", "signed_cd"}


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


def validate_asset_registry() -> None:
    if not REGISTRY_PATH.is_file():
        fail("assets.json is missing")
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if data.get("schema_version") != "1.0.0":
        fail("unsupported asset schema_version")

    storefront = data.get("storefront") or {}
    if storefront.get("payment_urls_fabricated") is not False:
        fail("payment_urls_fabricated must remain false")
    if storefront.get("dns_state") != "not_changed_by_this_branch":
        fail("store branch may not claim a DNS change")

    assets = data.get("assets")
    if not isinstance(assets, list) or not assets:
        fail("assets must be a non-empty list")
    ids: set[str] = set()
    hash_errors: list[str] = []
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
            hash_errors.append(
                f"{path.relative_to(ROOT)} expected={expected_hash} actual={actual_hash}"
            )
    if hash_errors:
        fail("asset SHA-256 mismatches:\n" + "\n".join(hash_errors))

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
        formats = set(product.get("formats") or [])
        if not REQUIRED_FORMATS.issubset(formats):
            fail(f"product {sku} does not expose all launch formats")


def validate_commerce_registry() -> None:
    if not COMMERCE_PATH.is_file():
        fail("commerce.json is missing")
    commerce = json.loads(COMMERCE_PATH.read_text(encoding="utf-8"))
    if commerce.get("schema_version") != "1.0.0":
        fail("unsupported commerce schema_version")
    if commerce.get("status") != "active":
        fail("commerce registry must be active")
    if commerce.get("currency") != "USD":
        fail("commerce currency must be USD")
    if commerce.get("canonical_path") != "https://iambandobandz.com/store/":
        fail("commerce canonical path drifted")
    if set(commerce.get("catalog_skus") or []) != REQUIRED_SKUS:
        fail("commerce SKU set drifted")

    attribution = commerce.get("attribution") or {}
    if attribution.get("query_parameter") != "client_reference_id":
        fail("checkout attribution must use client_reference_id")

    formats = commerce.get("formats") or {}
    if set(formats) != REQUIRED_FORMATS:
        fail(f"commerce format set drifted: {sorted(formats)}")

    for format_key, entry in formats.items():
        price_cents = entry.get("price_cents")
        if not isinstance(price_cents, int) or price_cents <= 0:
            fail(f"{format_key} price_cents must be a positive integer")
        for field, prefix in (
            ("stripe_product_id", "prod_"),
            ("stripe_price_id", "price_"),
            ("stripe_payment_link_id", "plink_"),
        ):
            value = entry.get(field)
            if not isinstance(value, str) or not value.startswith(prefix):
                fail(f"{format_key} has invalid {field}")
        parsed = urlparse(entry.get("checkout_url") or "")
        if parsed.scheme != "https" or parsed.netloc != "buy.stripe.com":
            fail(f"{format_key} checkout_url must use https://buy.stripe.com")


def validate_site_boundary() -> None:
    for relative in (
        "store/index.html",
        "store/styles.css",
        "store/store.js",
        "store/commerce.json",
        "store/thanks/index.html",
    ):
        if not (ROOT / relative).is_file():
            fail(f"required storefront file missing: {relative}")
    cname = (ROOT / "CNAME").read_text(encoding="utf-8").strip()
    if cname != EXPECTED_CNAME:
        fail(f"CNAME boundary changed unexpectedly: {cname!r}")

    script = (STORE / "store.js").read_text(encoding="utf-8")
    for required in ("/store/commerce.json", "client_reference_id", "checkout_start"):
        if required not in script:
            fail(f"store.js missing commerce binding: {required}")


def main() -> int:
    validate_site_boundary()
    validate_asset_registry()
    validate_commerce_registry()
    print("Store validation passed: assets, hashes, SKUs, Stripe commerce, attribution, and CNAME are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
