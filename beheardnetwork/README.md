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
- In this independent candidate, paid checkout is deliberately disabled: generated pages replace Stripe links with a launch-gate notice, and generated `network/offer.json` sets `checkout_enabled: false` and omits `checkout_url`. Re-enable only after the Payment Link fields and return URLs, signed webhook/D1 order intake, approved B Heard policies, and a named fulfillment operator with real delivery capacity are verified. This build-only gate does not change the existing artist-site page or Stripe account.
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



## Deployment architecture decision — 2026-11-27

**Decision:** use an independent Cloudflare Pages project for the static frontend, a Cloudflare Worker for the API and Stripe webhook, D1 for structured records, R2 for audio/media, and Turnstile for public-form abuse controls. The proposed origin is \`https://bheardnetwork.com/\`; it is not a route beneath \`iambandobandz.com\`.

This design needs **no home server, no inbound tunnel, no router access, and no port forwarding**. A Cloudflare Tunnel is not required for the public platform. It is only an optional outbound-only path for a future private admin service if an existing private host is deliberately chosen; it is not a production dependency.

### Service boundaries

- **Cloudflare Pages:** publish only the output of \`python3 tools/build_bheard_site.py --output dist/bheardnetwork\`. Keep the artist-site Pages project separate. Do not use a GitHub Pages branch-root artifact as the B Heard backend.
- **Cloudflare Worker:** own same-origin \`/api/*\` requests, authentication callbacks, submission intake, upload authorization, voting, health checks, and Stripe webhooks. A same-origin route avoids unnecessary browser CORS complexity.
- **D1:** hold creator profiles, submission metadata, moderation state, votes, media metadata, orders, webhook event IDs, campaign assignments, fulfillment actions, and receipts. Keep audio bytes out of SQL rows.
- **R2:** hold private/quarantined uploads and approved audio objects. The Worker issues short-lived upload authorization, validates metadata and content, and only publishes approved objects.
- **Turnstile:** protect anonymous intake and sensitive actions. Server-side verification is mandatory; a browser widget alone is not an abuse control.

### Rollout order

**Phase 1 — prove the revenue loop before building the social network**

1. Deploy the independent static landing and creator-promotion pages to a Cloudflare Pages preview.
2. Keep \`checkout_enabled: false\` until the independent Payment Link, exact offer/price, return URLs, signed webhook, D1 order record, B Heard-specific terms/refund/privacy notices, and named fulfillment operator are verified.
3. Use the Worker webhook to verify the Stripe signature, retrieve the authoritative Checkout Session, validate exact product/price/currency and paid status, and insert one idempotent D1 order.
4. Keep the order at \`paid_pending_fulfillment\`. A human operator assigns and performs the promotion, records timestamped actions and observed metrics, and issues a closing receipt. A Stripe redirect is never payment proof and a payment is never proof of delivery.
5. Reconcile refunds and disputes against the same order ID. Do not promise streams, followers, playlist placement, or algorithmic outcomes.

This phase does not require public creator accounts. It is the shortest path to a real paid order and a real, auditable promotion without pretending the social platform is finished.

**Phase 2 — creator identity, profiles, submissions, audio, and voting**

- Add Google OAuth using OpenID Connect Authorization Code + PKCE through the Worker, with validated state, nonce, issuer, audience, signature and expiry. Store the OAuth client secret and session-signing key as Worker secrets, never in the repository or browser.
- Use a server-issued \`HttpOnly; Secure; SameSite=Lax\` session cookie, CSRF protection on state-changing requests, short session lifetime, explicit logout, and server-side authorization checks. Do not put access tokens or passwords in localStorage.
- Add D1 tables for \`creator_profiles\`, \`submissions\`, \`media_objects\`, \`votes\`, \`moderation_events\`, \`orders\`, \`webhook_events\`, \`campaign_actions\`, and \`fulfillment_receipts\`.
- Give each submission an explicit lifecycle: draft, pending moderation, approved, rejected, archived. Public visibility is a server decision, not a client flag.
- Upload audio to a private R2 quarantine prefix using short-lived authorization. Validate actual file signatures, allowed codecs, MIME, size, duration and checksum; scan/moderate before publication. Store the R2 key and media metadata in D1. Test mobile playback, seeking, range requests, and interrupted uploads before release.
- Make voting server-authoritative. Enforce a database uniqueness constraint equivalent to \`UNIQUE(submission_id, voter_id)\`, require an authenticated voter, apply per-account rate limits and Turnstile to suspicious/high-risk actions, and retain an auditable vote event. Use short-lived pseudonymous abuse signals rather than retaining raw IP/device fingerprints indefinitely. Browser counters are never authoritative votes.

### Analytics and operational evidence

The current independent candidate records funnel events in the visitor's browser only; it has no remote collector and cannot report site-wide traffic or conversions. When an approved collector exists, use a bounded event set:

- \`landing_view\`, \`offer_view\`, \`checkout_start\`, \`checkout_return_unverified\`
- \`stripe_payment_verified\` (server webhook only), \`order_created\`, \`campaign_assigned\`
- \`promotion_action_recorded\`, \`campaign_completed\`, \`receipt_issued\`, \`refund_dispute_reconciled\`

Do not send card data, passwords, full referrer URLs, or unnecessary personal information to analytics. Derive paid conversion only from a verified webhook/order record, not a browser event.

Add a public \`/api/health\` check and independent monitoring for the Pages routes, Worker, DNS resolution, TLS expiry, and webhook failure rate. A successful artist-site search/store probe does not verify B Heard uptime. No independent uptime monitor, DNS/TLS record, or B Heard production health check is verified by this candidate.

### Cost and free-tier boundaries

Pricing snapshot checked **2026-11-27** against the linked vendor documentation; prices and quotas can change.

| Component | Free allowance / price | Production limitation |
|---|---|---|
| Cloudflare Pages | Free: 500 builds/month, 20,000 files/site, 25 MiB per asset | Audio larger than 25 MiB belongs in R2, not the Pages artifact |
| Workers | Free: 100,000 requests/day and 10 milliseconds CPU per invocation | Workers Paid starts at $5/month; includes 10 million requests/month and 30 million CPU-ms, then usage overage |
| D1 | Free: 5 million rows read/day, 100,000 rows written/day, 5 GB total | Paid includes 25 billion rows read/month, 50 million rows written/month and 5 GB storage before overage |
| R2 Standard | Free: 10 GB-month, 1 million Class A and 10 million Class B operations/month; internet egress free | Standard overage: $0.015/GB-month, $4.50/million Class A and $0.36/million Class B |
| Turnstile | Free: unlimited challenges, up to 20 widgets and 10 hostnames/widget | Free tier is suitable for the initial public forms; verify hostname configuration |
| Supabase alternative | Free: 50,000 MAU, 500 MB database, 1 GB file storage | Free projects pause after one week of inactivity; Pro starts at $25/month, includes 8 GB database, 100 GB file storage and 7-day daily backups |

Official references: [Pages limits](https://developers.cloudflare.com/pages/platform/limits/), [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/), [D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/), [R2 pricing](https://developers.cloudflare.com/r2/pricing/), [Turnstile plans](https://developers.cloudflare.com/turnstile/plans/), and [Supabase pricing](https://supabase.com/pricing).

**Recommended budget:** $0 for static preview and bounded development. For a small production revenue MVP, budget at least **$5/month** for Workers Paid, plus domain registration, Stripe processing, any email provider, and usage overages. Pages, D1 and R2 can remain within their published allowances at low volume, but free daily D1/Worker limits can stop requests when exceeded. Configure usage alerts, application rate limits, upload caps, and query indexes before accepting public traffic. This is a cost estimate, not an authorization to purchase or upgrade anything.

Supabase is the lower-code alternative if managed auth/Postgres/storage is more valuable than the lowest recurring cost. Its Free plan is a prototype tier because projects pause after inactivity; its Pro plan is $25/month. Do not create a Supabase project or connect a provider without approval.

### Current security and deployment blocker

The current main branch still contains the legacy \`bheardnetwork/\` prototype. Its API shim accepts an arbitrary \`?api=\` URL, probes that origin, then rewrites same-page \`/api/*\` requests to it. The legacy application sends login/registration request bodies through that shim. A crafted link can therefore route credentials to an attacker-controlled API origin if a visitor signs in through the legacy page. This is a source-level credential-routing vulnerability; no exploitation or credential theft is established.

The independent builder in this PR excludes the legacy route from its sanitized artist-site output, but that protection is not live until the sanitized deployment path is actually used. On 2026-11-27, main commit \`6f349fa4c85cf0832dafb4e3a806c6ab51bd42aa\` had:

- Deploy IAMBANDOBANDZ run [#46069801983](https://github.com/MASSIVEMAGNETICS/MASSIVEMAGNETICS.github.io/actions/runs/46069801983): **FAILURE** at site tests; 74 tests, 2 failures, 1 error, 3 skipped. Missing \`bheardnetwork/logo.jpg\` and \`bheardnetwork/demo-media/1.wav\`; sanitized build/upload/deploy steps were skipped.
- Default Pages build [#46069790001](https://github.com/MASSIVEMAGNETICS/MASSIVEMAGNETICS.github.io/actions/runs/46069790001): **SUCCESS**, but its published artifact contains the legacy \`bheardnetwork/\`, \`network/\`, and \`beheardnetwork/\` route trees.
- Scheduled artist-site verification [#46079819945](https://github.com/MASSIVEMAGNETICS/MASSIVEMAGNETICS.github.io/actions/runs/46079819945): **SUCCESS** for artist search/identity and store synchronization only; it does not verify B Heard.

The existing PR #59 is the demo-asset repair; do not duplicate it. PR #58 is the independent-root builder. Both need current-base integration and exact-head CI before the sanitized Pages artifact can be trusted. The proposed independent domain, DNS, TLS and uptime remain **UNKNOWN**, not verified live.

### Release and rollback gates

Before any production launch, require: exact-head CI; sanitized artifact inspection proving the old route trees are absent from the artist origin; independent Pages preview acceptance; verified domain ownership and TLS; deployed Worker/D1/R2 staging; provider/OAuth and session tests; Stripe test-mode webhook acceptance and idempotency tests; approved B Heard-specific legal/policy pages; a named fulfillment operator; a complete dummy-order fulfillment receipt; and an independent uptime/security probe.

No DNS, TLS, production secret, billing, paid plan, live webhook, checkout activation, payment, customer message, or production deployment is authorized by this documentation change. Keep the independent checkout disabled until each gate has evidence and the owner explicitly approves the relevant production action.

Rollback this documentation/test addition by reverting its commits on this existing draft branch or closing PR #58. No production resource is changed.
