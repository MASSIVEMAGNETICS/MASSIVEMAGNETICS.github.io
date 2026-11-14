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
