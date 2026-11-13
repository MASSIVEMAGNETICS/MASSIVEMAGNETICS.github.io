# B Heard independent order intake — review candidate

This **undeployed** Cloudflare Worker receives signed Stripe Checkout events for the B Heard $9.99 creator-promotion offer. It does not run on GitHub Pages, does not require a home server, and does **not** deliver promotions or send customer messages. Source can move to an independent B Heard repository before production.

## Runtime contract

- Cloudflare Workers module entry: `src/worker.mjs`.
- Route: `POST /webhooks/stripe` on a separately authorized B Heard backend origin.
- D1 database binding: `DB`; apply `migrations/0001_orders.sql` before activation.
- Secret bindings: `STRIPE_WEBHOOK_SECRET`, `STRIPE_SECRET_KEY` (live credentials only in deployed secrets, never committed).
- Plaintext environment binding: `BHEARD_PAYMENT_LINK_ID` = `plink_1U5HMjCpO4d12HbZcK2NQg5p` for live mode. `BHEARD_EXPECT_LIVEMODE` defaults to `true`; set to `false` **only** in an isolated test environment with test keys and a test Payment Link ID.
- Only `checkout.session.completed` and `checkout.session.async_payment_succeeded` are candidates. The handler verifies the raw-body HMAC and freshness, then fetches the authoritative Checkout Session from Stripe. It checks live mode, exact Payment Link, offer metadata, $9.99 USD and paid status before writing.
- D1 atomic batch and primary-key constraints make duplicate session deliveries order-idempotent. Invalid creator intake is recorded as `needs_intake` for manual resolution. No order is automatically fulfilled.
- A transient Stripe API or D1 failure returns 503 to trigger retry. Do not enable the live webhook until there is monitoring and a manual Stripe-session reconciliation/replay process; Stripe's retry window is finite.

## Offline tests

Run from repository root: `node --test bheard-order-worker/test/*.test.mjs` (Node.js 22 or newer). No npm dependencies, Stripe credentials, or network access required. The test database models unique session/event constraints; validate D1 migrations separately before deployment.

## Production approval gate

1. Provision an **independent** B Heard origin, a Worker route, D1 database and secrets (owner approval required).
2. Apply migration and verify schema/rollback in an isolated test database.
3. Exercise a signed Stripe test-mode event end-to-end, including duplicate and delayed-payment delivery, and verify exactly one order.
4. Configure operational alerts and periodic paid-Checkout reconciliation so missed webhooks can be recovered.
5. Define manual fulfillment steps and receipt evidence; do not equate `paid_pending_fulfillment` with delivery.
6. Only after explicit approval: configure a live Stripe webhook, verify the exact endpoint, and promote a tested build. Never commit secrets, automatically send messages, merge, deploy, change DNS/billing, or initiate payments.

**Known limitations:** no first-party auth, creator profile, media ingestion, voting, fraud detection, analytics collector, admin fulfillment interface, refunds/disputes processor, or independent domain. All remain separate launch gates. D1 and Workers free tiers have limits and are not an uptime SLA.
