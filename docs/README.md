# Public Site Operations Documentation

Canonical brand: `iambandobandz`  
Canonical domain: `https://iambandobandz.com/`

## Operational documents

- [`CHATGPT_WORK_ORDER_PUBLIC_PLATFORM_SEO.md`](./CHATGPT_WORK_ORDER_PUBLIC_PLATFORM_SEO.md) — approved implementation contract for canonical search identity, public information architecture, B Heard platform evolution, verification, and merge gates.
- [`POST_DEPLOY_VERIFICATION.md`](./POST_DEPLOY_VERIFICATION.md) — live-site verification and search-engine follow-up procedure.

## Source-of-truth hierarchy

1. `registry/public/*.json` — canonical public identity, entities, platforms, catalog, and route registry.
2. `tools/registry_lib.py` — deterministic structured-data/sitemap/manifest generation.
3. `tools/build_site.py` — sanitized deploy artifact construction.
4. `tests/` — regression contracts.
5. `.github/workflows/site-ci.yml` — pre-merge verification.
6. `.github/workflows/deploy.yml` — production Pages deployment.
7. `.github/workflows/post-deploy-verify.yml` — live deployment verification.

Generated artifacts should be fixed by changing the source-of-truth registry/build path, not by hand-editing the deployed output.
