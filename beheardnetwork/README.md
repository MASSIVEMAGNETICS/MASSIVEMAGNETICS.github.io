# B Heard Network — independent static-site candidate

This directory contains the brand assets and browser-local instrumentation used by the independent B Heard build target. The actual deployable root is generated from the existing B Heard source pages by:

```bash
python3 tools/build_bheard_site.py --output dist/bheardnetwork
```

For a Cloudflare Pages project, the candidate settings are:

- Repository root: `/`
- Build command: `python3 tools/build_bheard_site.py --output dist/bheardnetwork`
- Build output directory: `dist/bheardnetwork`

The output contains `/`, `/network/`, `/network/board/`, and `/network/thanks/`. It is a separate static root; it is not the current `iambandobandz.com/beheardnetwork/` subpage build.

## Origin and deployment gate

The builder emits `https://bheardnetwork.com` as the proposed canonical origin. This PR does **not** verify domain ownership, DNS, TLS, Cloudflare account configuration, or public uptime. The repository's existing `CNAME` still points to `iambandobandz.com`. Do not attach the proposed custom domain or change DNS based only on this candidate.

## Current functional boundaries

- The board is a public GitHub-Issues read layer. Posting/replying requires a GitHub account. There is no first-party B Heard identity provider or creator-profile database.
- The $9.99 creator-promotion link is an external Stripe Payment Link. This build does not inspect the Stripe account, create a payment, or prove the link is active.
- The signed Stripe-to-D1 Worker in PR #57 is a separate unmerged candidate. No Worker, D1 database, R2 bucket, secret, webhook, or production resource is provisioned here.
- The checkout-return correction in PR #56 remains a separate review item. A redirect is not payment verification.
- No production audio ingestion, durable media library, or real uploaded-track player is included. The Library prototype is not part of this build.
- No server-side voting, rate limiting, identity binding, or anti-fraud voting service is included. Do not publish prototype counters as real votes.
- Funnel events are stored in each visitor's browser. No remote analytics collector is configured, so this build cannot produce site-wide traffic or conversion totals.
- `_headers` supplies baseline browser security headers. A restrictive CSP and HSTS require staging validation against the final origin and third-party integrations.

This is a buildable static candidate, not a live or production-ready platform.


## Commercial and fulfillment launch gate — NOT CLEARED

The source artifact `network/terms/index.html` is marked **DRAFT / not published** and describes the offer at `iambandobandz.com/network/`. It is not an approved B Heard-specific policy for the proposed independent origin. This build intentionally does not copy that draft; the current privacy and terms links remain explicit cross-site links to the artist site.

Do not enable the independent paid funnel until the owner approves and publishes B Heard-specific terms, refund policy, and privacy notice on the independent origin. The current draft's section 8.4 gives broad discretion to deny refunds; that clause requires owner/legal review before adoption. This note is an operational gate, not legal advice.

No campaign fulfillment owner or current delivery capacity has been independently verified. Until that is documented, fulfillment must remain human-reviewed. A Stripe payment or browser redirect alone must never mark a campaign fulfilled.

Required closure evidence:

1. Verified paid Checkout Session and stable Stripe session ID.
2. One durable D1 order record and validated creator intake.
3. Named fulfillment operator and timestamped campaign assignment.
4. Timestamped promotion actions and observed metrics, without guaranteed outcomes.
5. Closing receipt delivered through an approved channel.
6. Refund/dispute status reconciled against the same order.

