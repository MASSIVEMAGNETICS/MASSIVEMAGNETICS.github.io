#!/usr/bin/env python3
"""Build B Heard Network as an independent static-site root.

This builder only copies and rewrites local source files. It does not call
external services, provision resources, modify DNS, or deploy anything.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://bheardnetwork.com"

COPY_FILES = (
    ("beheardnetwork/index.html", "index.html"),
    ("network/index.html", "network/index.html"),
    ("network/board/index.html", "network/board/index.html"),
    ("network/board/board.css", "network/board/board.css"),
    ("network/board/board.js", "network/board/board.js"),
    ("network/thanks/index.html", "network/thanks/index.html"),
    ("network/offer.json", "network/offer.json"),
    ("styles.css", "styles.css"),
    ("beheardnetwork/brand.css", "brand.css"),
    ("beheardnetwork/analytics.js", "analytics.js"),
    ("beheardnetwork/_headers", "_headers"),
    ("beheardnetwork/assets/bheard-network-logo.svg", "assets/bheard-network-logo.svg"),
)

CANONICAL_URLS = {
    "index.html": f"{ORIGIN}/",
    "network/index.html": f"{ORIGIN}/network/",
    "network/board/index.html": f"{ORIGIN}/network/board/",
}

HOME_WORDMARK = (
    '<a class="wordmark" href="/" aria-label="IAMBANDOBANDZ home">B HEARD NETWORK</a>'
)
BOARD_WORDMARK = (
    '<a class="wordmark" href="/network/" aria-label="B Heard Network home">B HEARD NETWORK</a>'
)
INDEPENDENT_WORDMARK = (
    '<a class="wordmark" href="/" aria-label="B Heard Network home">'
    '<img class="bheard-logo" src="/assets/bheard-network-logo.svg" alt="">'
    '<span>B HEARD NETWORK</span></a>'
)

LEGACY_CHECKOUT_COPY = (
    "If Stripe redirected you here after completing checkout, keep the Stripe receipt "
    "sent to your checkout email. That receipt is the payment record."
)
SAFE_CHECKOUT_COPY = (
    "You have returned from Stripe Checkout. This page cannot confirm whether a payment "
    "succeeded. Keep any Stripe receipt you receive; campaign intake and promotion begin "
    "only after payment and required information are independently verified."
)
LEGACY_INTAKE_COPY = (
    "Your creator name, release/project URL, and campaign goal were collected in Stripe "
    "Checkout and are used to reconcile the campaign intake. For support, email "
    '<a href="mailto:bandobandz440@gmail.com?subject=B%20Heard%20campaign%20support">'
    "bandobandz440@gmail.com</a>."
)
SAFE_INTAKE_COPY = (
    "If you submitted creator information in Stripe Checkout, it will be reconciled "
    "against a verified paid order before promotion begins. For support, email "
    '<a href="mailto:bandobandz440@gmail.com?subject=B%20Heard%20campaign%20support">'
    "bandobandz440@gmail.com</a>."
)
LEGACY_CHECKOUT_EVENT = (
    "window.dataLayer.push({ event: 'checkout_return', funnel: 'bheard-network', "
    "offer_code: 'bheard_creator_promo_v1' });"
)
SAFE_CHECKOUT_EVENT = (
    "window.dataLayer.push({ event: 'checkout_return_unverified', funnel: 'bheard-network', "
    "offer_code: 'bheard_creator_promo_v1' });"
)


def replace_once(value: str, old: str, new: str, label: str) -> str:
    count = value.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one exact source anchor, found {count}")
    return value.replace(old, new, 1)


def enforce_independent_checkout_gate(page: str, source_relative: str) -> str:
    """Keep the independent candidate from accepting payment before its full revenue loop is verified."""
    if source_relative == "network/index.html":
        page = replace_once(
            page,
            "Secure Stripe checkout active",
            "Independent campaign checkout not enabled",
            "independent checkout status",
        )
        page = replace_once(
            page,
            "Stripe Checkout collects the creator/project information attached to the order.",
            "The independent site's required creator/project intake fields and their persistence have not yet been verified.",
            "independent creator intake claim",
        )
        page = replace_once(
            page,
            "Checkout is hosted by Stripe. Your campaign fields and payment are attached to the order so the promotion can be reconciled without guessing which creator or release paid.",
            "The independent payment link, required intake fields, webhook/order intake, and fulfillment process have not yet been verified. No campaign is accepted or started from this page until a paid order and complete intake are independently reconciled.",
            "independent checkout/order claim",
        )

    if source_relative == "network/board/index.html":
        page = replace_once(
            page,
            "Dropping music on the board is free. If you want a bounded B Heard creator-promotion campaign, the existing $9.99 service remains the paid lane. Promotion work and outcomes are measured; streams, placements, followers, and algorithmic results are never guaranteed.",
            "Dropping music on the board is free. Paid creator-promotion checkout is not enabled on the independent site yet. Availability, intake, approved policies, and fulfillment must be verified before the paid service is offered here.",
            "independent board paid-service claim",
        )
        page = replace_once(
            page,
            'data-board-action="creator-promo"',
            'data-board-action="campaign-availability"',
            "independent board campaign action",
        )

    if source_relative == "beheardnetwork/index.html":
        page = replace_once(
            page,
            "handled through secure Stripe checkout.",
            "enabled only after the independent payment and fulfillment gates are cleared.",
            "independent checkout security claim",
        )

    if source_relative in ("beheardnetwork/index.html", "network/index.html"):
        legacy_click_script = """<script>
  document.querySelectorAll('a[href^="https://buy.stripe.com/"]').forEach((link) => {
    link.addEventListener('click', () => {
      window.dataLayer = window.dataLayer || [];
      window.dataLayer.push({ event: 'checkout_start', funnel: 'bheard-network', offer_code: 'bheard_creator_promo_v1', value: 9.99, currency: 'USD' });
    });
  });
</script>"""
        page = replace_once(
            page, legacy_click_script, "", "independent checkout click tracking"
        )

    checkout_link_pattern = re.compile(
        r'(<a\b[^>]*\bhref=")(https://buy\.stripe\.com/[^"]+)("[^>]*>)(.*?)(</a>)',
        re.IGNORECASE | re.DOTALL,
    )
    page, replaced = checkout_link_pattern.subn(
        lambda match: (
            match.group(1)
            + "#campaign-launch-gate"
            + match.group(3)
            + "Campaign checkout pending"
            + match.group(5)
        ),
        page,
    )
    if replaced < 1:
        raise RuntimeError(
            f"{source_relative}: expected at least one Stripe checkout link, found {replaced}"
        )

    notice = """<section class="contact-section" id="campaign-launch-gate">
  <p class="eyebrow">PAID CAMPAIGN LAUNCH GATE</p>
  <h2>CHECKOUT<br><em>NOT ENABLED YET.</em></h2>
  <p>The independent B Heard site is not accepting paid campaigns yet. The payment link, required intake fields, webhook/order intake, approved policies, and fulfillment capacity must be verified before checkout can be enabled. No payment is taken from this independent site.</p>
  <div class="contact-actions"><a class="button button-primary" href="mailto:bandobandz440@gmail.com?subject=B%20Heard%20campaign%20availability">Check campaign availability</a></div>
</section>
"""
    page = replace_once(page, "</main>", notice + "</main>", "independent checkout launch gate")
    if "buy.stripe.com/" in page or "checkout_start" in page:
        raise RuntimeError(f"{source_relative}: checkout remained exposed after gating")
    return page


def ensure_legacy_or_safe(value: str, legacy: str, safe: str, label: str) -> str:
    """Upgrade one legacy anchor or accept exactly one already-hardened anchor."""
    legacy_count = value.count(legacy)
    safe_count = value.count(safe)
    if legacy_count == 1 and safe_count == 0:
        return replace_once(value, legacy, safe, label)
    if legacy_count == 0 and safe_count == 1:
        return value
    raise RuntimeError(
        f"{label}: expected exactly one legacy or safe anchor; "
        f"found legacy={legacy_count}, safe={safe_count}"
    )


def enforce_checkout_return_boundary(page: str) -> str:
    """Never let a Stripe redirect or browser event masquerade as payment proof."""
    page = ensure_legacy_or_safe(
        page, LEGACY_CHECKOUT_COPY, SAFE_CHECKOUT_COPY, "checkout return payment boundary"
    )
    page = ensure_legacy_or_safe(
        page, LEGACY_INTAKE_COPY, SAFE_INTAKE_COPY, "checkout return intake boundary"
    )
    page = ensure_legacy_or_safe(
        page, LEGACY_CHECKOUT_EVENT, SAFE_CHECKOUT_EVENT, "checkout return telemetry"
    )
    return page


MOBILE_NAV_SCRIPT = """<script>
(() => {
  'use strict';
  const button = document.querySelector('.menu-toggle');
  const nav = document.querySelector('#primary-nav');
  if (!button || !nav) return;
  const setOpen = (open) => {
    nav.classList.toggle('open', open);
    button.setAttribute('aria-expanded', String(open));
  };
  button.addEventListener('click', () => {
    setOpen(button.getAttribute('aria-expanded') !== 'true');
  });
  nav.addEventListener('click', (event) => {
    if (event.target.closest('a[href]')) setOpen(false);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') setOpen(false);
  });
})();
</script>"""


def ensure_mobile_navigation(page: str, source_relative: str) -> str:
    """Add the accessible menu control required by the shared responsive CSS."""
    if 'class="nav-links"' not in page:
        return page
    if 'class="menu-toggle"' in page or 'id="primary-nav"' in page:
        raise RuntimeError(f"{source_relative}: mobile navigation is partially configured")

    pattern = re.compile(
        r'(<a class="wordmark"[^>]*>.*?</a>\s*)<nav class="nav-links"',
        re.DOTALL,
    )
    page, count = pattern.subn(
        lambda match: (
            match.group(1)
            + '<button class="menu-toggle" type="button" aria-label="Toggle navigation" '
            + 'aria-expanded="false" aria-controls="primary-nav">MENU</button>\n  '
            + '<nav id="primary-nav" class="nav-links"'
        ),
        page,
        count=1,
    )
    if count != 1:
        raise RuntimeError(f"{source_relative}: expected one wordmark/navigation pair, found {count}")
    return replace_once(
        page,
        "</body>",
        MOBILE_NAV_SCRIPT + "\n</body>",
        f"{source_relative} mobile navigation",
    )


def copy_source(source_relative: str, destination: Path) -> None:
    source = ROOT / source_relative
    if not source.is_file():
        raise FileNotFoundError(f"required B Heard source missing: {source_relative}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def rewrite_page(source_relative: str, destination_relative: str, output: Path) -> None:
    source = ROOT / source_relative
    page = source.read_text(encoding="utf-8")

    if source_relative in ("beheardnetwork/index.html", "network/index.html", "network/board/index.html"):
        page = enforce_independent_checkout_gate(page, source_relative)

    if source_relative == "network/thanks/index.html":
        page = enforce_checkout_return_boundary(page)

    canonical = CANONICAL_URLS.get(destination_relative)
    if canonical:
        pattern = re.compile(r'<link rel="canonical" href="[^"]+"\s*/?>')
        page, count = pattern.subn(
            f'<link rel="canonical" href="{canonical}">', page, count=1
        )
        if count != 1:
            raise RuntimeError(f"{source_relative}: canonical link missing or ambiguous")

    if source_relative in ("beheardnetwork/index.html", "network/index.html"):
        page = replace_once(page, HOME_WORDMARK, INDEPENDENT_WORDMARK, source_relative)
    elif source_relative == "network/board/index.html":
        page = replace_once(page, BOARD_WORDMARK, INDEPENDENT_WORDMARK, source_relative)

    if source_relative in ("beheardnetwork/index.html", "network/index.html", "network/board/index.html"):
        page = ensure_mobile_navigation(page, source_relative)

    # B Heard remains the destination root. Artist/Empire surfaces are explicit
    # cross-site links, never accidental root-relative paths on the B Heard host.
    page = page.replace('<a href="/">Empire</a>', '<a href="https://iambandobandz.com/">Empire</a>')
    page = page.replace('href="/store/"', 'href="https://iambandobandz.com/store/"')
    page = page.replace('href="/proof/"', 'href="https://iambandobandz.com/proof/"')
    page = page.replace('href="/privacy/"', 'href="https://iambandobandz.com/privacy/"')
    page = page.replace('href="/terms/"', 'href="https://iambandobandz.com/terms/"')
    page = page.replace(
        'href="/">IAMBANDOBANDZ HOME</a>',
        'href="https://iambandobandz.com/">IAMBANDOBANDZ HOME</a>',
    )

    # The source count was not independently verified. Do not publish it as fact.
    page = page.replace("a 20,000-member artist community", "a community for independent artists")
    page = page.replace("A 20,000-member artist community", "A community for independent artists")
    page = page.replace("20,000-member artist community", "independent-artist community")

    styles_tag = '<link rel="stylesheet" href="/styles.css">'
    if styles_tag not in page:
        raise RuntimeError(f"{source_relative}: shared stylesheet reference missing")
    if 'href="/brand.css"' not in page:
        page = page.replace(
            styles_tag,
            styles_tag + '\n  <link rel="stylesheet" href="/brand.css">',
            1,
        )

    if source_relative == "network/thanks/index.html":
        brand = (
            '<div class="wordmark bheard-return-brand">'
            '<img class="bheard-logo" src="/assets/bheard-network-logo.svg" alt="">'
            '<span>B HEARD NETWORK</span></div>\n  '
        )
        page = replace_once(
            page,
            '<p class="eyebrow">B HEARD NETWORK / CHECKOUT RETURN</p>',
            brand + '<p class="eyebrow">B HEARD NETWORK / CHECKOUT RETURN</p>',
            "checkout return brand",
        )

    if 'src="/analytics.js"' not in page:
        page = replace_once(
            page,
            "</body>",
            '<script src="/analytics.js" defer></script>\n</body>',
            f"{source_relative} analytics script",
        )

    destination = output / destination_relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(page, encoding="utf-8")


def build(output: Path) -> Path:
    """Build a marked output directory without deleting unrecognized data."""
    raw_output = Path(output).expanduser()
    if raw_output.is_symlink():
        raise RuntimeError(f"refusing symlink output directory: {raw_output}")
    output = raw_output.resolve()
    if output == ROOT or output in ROOT.parents:
        raise RuntimeError(f"refusing unsafe output path: {output}")
    if ROOT in output.parents and (ROOT / "dist") not in output.parents:
        raise RuntimeError("repository-local output must be inside dist/")

    marker = output / ".bheard-build"
    marker_text = (
        "Generated by tools/build_bheard_site.py. Safe to replace on the next build.\n"
    )
    if output.exists():
        if not marker.is_file() or marker.read_text(encoding="utf-8") != marker_text:
            raise RuntimeError(
                f"refusing to replace unmarked output directory: {output}"
            )
        shutil.rmtree(output)

    output.mkdir(parents=True)
    for source_relative, destination_relative in COPY_FILES:
        if source_relative.endswith(".html"):
            rewrite_page(source_relative, destination_relative, output)
        else:
            copy_source(source_relative, output / destination_relative)

    # Fail closed if any copied HTML route still exposes the unverified Stripe URL.
    for html_path in output.rglob("*.html"):
        if "buy.stripe.com/" in html_path.read_text(encoding="utf-8"):
            raise RuntimeError(
                f"unverified checkout URL remains in independent output: {html_path.relative_to(output)}"
            )

    offer_path = output / "network" / "offer.json"
    offer = json.loads(offer_path.read_text(encoding="utf-8"))
    if offer.get("offer_code") != "bheard_creator_promo_v1":
        raise RuntimeError("unexpected B Heard offer code; refusing to rewrite registry")
    offer["canonical_path"] = f"{ORIGIN}/network/"
    offer["checkout_enabled"] = False
    offer["checkout_status"] = "pending_independent_verification"
    stripe = offer.get("stripe")
    if isinstance(stripe, dict):
        stripe.pop("checkout_url", None)
    offer_path.write_text(json.dumps(offer, indent=2) + "\n", encoding="utf-8")

    (output / "robots.txt").write_text(
        "User-agent: *\nAllow: /\nDisallow: /network/thanks/\n",
        encoding="utf-8",
    )
    marker.write_text(marker_text, encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "dist" / "bheardnetwork",
        help="generated output directory (default: dist/bheardnetwork)",
    )
    args = parser.parse_args()
    try:
        output = build(args.output)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(1, f"B Heard site build failed: {exc}\n")
    print(f"B Heard independent static root built at {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
