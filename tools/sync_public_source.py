from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

from build_site import build
from registry_lib import ROOT


SYNC_PATHS = (
    "index.html",
    "portfolio/index.html",
    "identity.jsonld",
    ".well-known/iambandobandz.json",
    "sitemap.xml",
)


def sync_public_source() -> list[str]:
    """Materialize generated search-critical artifacts into the repository source.

    GitHub Pages can be configured either for custom workflow deployments or
    legacy branch publishing. Keeping these search-critical files synchronized
    prevents the custom domain from serving stale raw-source identity metadata
    if the Pages publishing mode drifts or is changed outside the repository.
    """
    changed: list[str] = []
    with tempfile.TemporaryDirectory(prefix="iambandobandz-sync-") as tmp:
        site = Path(tmp) / "site"
        build(site)
        for relative in SYNC_PATHS:
            source = site / relative
            if not source.is_file():
                raise FileNotFoundError(f"generated public artifact missing: {relative}")
            destination = ROOT / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            new_bytes = source.read_bytes()
            old_bytes = destination.read_bytes() if destination.exists() else None
            if old_bytes != new_bytes:
                destination.write_bytes(new_bytes)
                changed.append(relative)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync generated public identity/search artifacts back to repository source")
    parser.parse_args()
    changed = sync_public_source()
    if changed:
        print("Synchronized:")
        for path in changed:
            print(f"- {path}")
    else:
        print("Public source already synchronized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
