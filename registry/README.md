# IAMBANDOBANDZ Canonical Data Registry

This directory is the source of truth for the public identity graph behind `iambandobandz.com`.

## Invariant

`registry -> validate -> build -> deploy -> verify`

The website is a projection of canonical state. Hand-edited HTML must not become the authoritative identity/catalog database.

## Layout

- `public/` — publishable entities, identity, platform IDs, catalog, and site profile.
- `schema/` — JSON Schema contracts for registry records.
- `contracts/` — API/event contracts for future private services.
- `private/` — guardrail only. No PII, consent ledger, customer database, or revenue ledger may be committed here.

The deploy workflow validates the registry, builds a sanitized `_site`, replaces homepage JSON-LD from registry state, generates the sitemap/public manifest, fixes portfolio canonical metadata, and excludes private scaffolding from the Pages artifact.
