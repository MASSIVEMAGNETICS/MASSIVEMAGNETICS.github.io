#!/usr/bin/env python3
"""Deterministically reconcile storefront derived metadata from one authority contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = ROOT / "store" / "sync-contract.json"
REGISTRY_PATH = ROOT / "store" / "assets" / "assets.json"
COMMERCE_PATH = ROOT / "store" / "commerce.json"
STORE_HTML_PATH = ROOT / "store" / "index.html"


class SyncError(RuntimeError):
    pass


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SyncError(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise SyncError(f"{path.relative_to(ROOT)} must contain a JSON object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def local_public_path(public_path: str) -> Path:
    if not isinstance(public_path, str) or not public_path.startswith("/"):
        raise SyncError(f"invalid public path: {public_path!r}")
    candidate = (ROOT / public_path.lstrip("/")).resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise SyncError(f"public path escapes repository: {public_path}") from exc
    return candidate


def reconcile() -> tuple[dict, list[str]]:
    contract = load_json(CONTRACT_PATH)
    registry = load_json(REGISTRY_PATH)
    commerce = load_json(COMMERCE_PATH)
    html = STORE_HTML_PATH.read_text(encoding="utf-8")

    if contract.get("schema_version") != "store-sync/1.0":
        raise SyncError("unsupported store sync contract")
    if commerce.get("schema_version") != "1.0.0":
        raise SyncError("unsupported commerce registry")
    if commerce.get("status") != "active":
        raise SyncError("commerce must be active before storefront reconciliation")

    releases = contract.get("releases")
    if not isinstance(releases, list) or not releases:
        raise SyncError("sync contract requires releases")

    assets = registry.get("assets")
    products = registry.get("products")
    if not isinstance(assets, list) or not isinstance(products, list):
        raise SyncError("asset registry must contain assets and products lists")

    asset_by_id = {item.get("id"): item for item in assets}
    product_by_sku = {item.get("sku"): item for item in products}
    commerce_skus = set(commerce.get("catalog_skus") or [])
    contract_skus = {item.get("sku") for item in releases}
    if commerce_skus != contract_skus:
        raise SyncError(
            f"SKU authority disagreement: commerce={sorted(commerce_skus)} contract={sorted(contract_skus)}"
        )

    changes: list[str] = []

    storefront = registry.setdefault("storefront", {})
    for key, expected in (
        ("canonical_path", commerce.get("canonical_path")),
        ("checkout_state", commerce.get("status")),
    ):
        if storefront.get(key) != expected:
            storefront[key] = expected
            changes.append(f"storefront.{key}")

    registry["registry_version"] = contract.get("revision", registry.get("registry_version"))
    asset_policy = registry.setdefault("asset_policy", {})
    asset_policy["canonical_release_source"] = "store/sync-contract.json"
    asset_policy["derived_format"] = "webp/svg"

    for release in releases:
        sku = release.get("sku")
        asset_id = release.get("art_asset")
        public_path = release.get("public_art_path")
        if sku not in product_by_sku:
            raise SyncError(f"sync contract references missing product {sku}")
        if asset_id not in asset_by_id:
            raise SyncError(f"sync contract references missing asset {asset_id}")

        asset = asset_by_id[asset_id]
        product = product_by_sku[sku]
        local_path = local_public_path(public_path)
        if not local_path.is_file():
            raise SyncError(f"canonical artwork is missing: {public_path}")

        if asset.get("path") != public_path:
            asset["path"] = public_path
            changes.append(f"{asset_id}.path")

        derived = asset.setdefault("derived", {})
        expected_hash = sha256(local_path)
        if derived.get("sha256") != expected_hash:
            derived["sha256"] = expected_hash
            changes.append(f"{asset_id}.sha256")
        if release.get("width") and derived.get("width") != release["width"]:
            derived["width"] = release["width"]
            changes.append(f"{asset_id}.width")
        if release.get("height") and derived.get("height") != release["height"]:
            derived["height"] = release["height"]
            changes.append(f"{asset_id}.height")
        derived["media_type"] = "image/svg+xml" if public_path.endswith(".svg") else "image/webp"

        if product.get("art_asset") != asset_id:
            product["art_asset"] = asset_id
            changes.append(f"{sku}.art_asset")
        if product.get("checkout_state") != commerce["status"]:
            product["checkout_state"] = commerce["status"]
            changes.append(f"{sku}.checkout_state")
        product["checkout_registry"] = "/store/commerce.json"

        marker = f'data-sku="{sku}"'
        if marker not in html:
            raise SyncError(f"storefront HTML is missing {sku}")
        start = html.index(marker)
        end = html.find("</article>", start)
        if end < 0:
            raise SyncError(f"storefront HTML article is malformed for {sku}")
        block = html[start:end]
        if f'src="{public_path}"' not in block:
            raise SyncError(
                f"rendered artwork drift for {sku}: expected src={public_path}"
            )

    return registry, changes


def canonical_json(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when store/assets/assets.json is not already reconciled",
    )
    args = parser.parse_args()

    expected, changes = reconcile()
    current = REGISTRY_PATH.read_text(encoding="utf-8")
    rendered = canonical_json(expected)

    if args.check:
        if current != rendered:
            raise SystemExit(
                "STORE SYNC DRIFT: registry is not canonical; run "
                "`python tools/reconcile_store_state.py`"
            )
        print("Store synchronization check passed.")
        return 0

    if current != rendered:
        REGISTRY_PATH.write_text(rendered, encoding="utf-8")
        print("Reconciled storefront state: " + ", ".join(changes))
    else:
        print("Storefront state already synchronized.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SyncError as exc:
        raise SystemExit(f"STORE SYNC FAILED: {exc}")
