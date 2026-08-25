# Post-Deploy Verification — iambandobandz.com

Use this checklist after the canonical search/platform PR is merged and the GitHub Pages deployment completes.

## Automated verification

Primary command:

```bash
python tools/verify_public_site.py \
  --base-url https://iambandobandz.com/ \
  --retries 8 \
  --delay 20
```

The `Post-Deploy Public Verification` GitHub Actions workflow runs this automatically after a successful `Deploy IAMBANDOBANDZ` workflow and can also be triggered manually.

A passing run verifies the deployed technical contract, not search-engine ranking.

## Required live checks

- [ ] `https://iambandobandz.com/` returns HTTP 200.
- [ ] Homepage title begins with `iambandobandz`.
- [ ] Homepage canonical URL is exactly `https://iambandobandz.com/`.
- [ ] Open Graph site name is `iambandobandz`.
- [ ] Built homepage contains no `Bando Bandz` artist alias.
- [ ] Built homepage contains no spaced `I AM BANDO BANDZ` identity phrase.
- [ ] `/robots.txt` points to `https://iambandobandz.com/sitemap.xml`.
- [ ] `/sitemap.xml` contains every approved current public route and no planned/dead route.
- [ ] `/site.webmanifest` uses `iambandobandz` as `short_name`.
- [ ] `/identity.jsonld` exposes exactly one canonical `MusicGroup` named `iambandobandz`.
- [ ] `/.well-known/iambandobandz.json` reports canonical brand and domain correctly.
- [ ] `/llms.txt` declares the same canonical brand/domain.
- [ ] `/portfolio/` canonical resolves to `iambandobandz.com`, not `massivemagnetics.github.io`.
- [ ] `/portfolio/` no longer depends on `chatgpt.site` social metadata.
- [ ] `/frontier-radar/` has an explicit canonical link to its `iambandobandz.com` route.
- [ ] Existing `/store/`, `/network/`, and `/audit/` revenue paths still resolve.

## Search-engine follow-up

Search indexing is asynchronous. After the technical verifier passes:

1. Submit or refresh `https://iambandobandz.com/sitemap.xml` in Google Search Console.
2. Submit or refresh the same sitemap in Bing Webmaster Tools.
3. Inspect the canonical homepage in both consoles and confirm the selected canonical is `https://iambandobandz.com/`.
4. Request indexing only after the live technical checks pass.
5. Search the exact branded query `iambandobandz` periodically and record:
   - whether the owned domain is indexed;
   - rank/position of the owned domain;
   - competing/duplicate artist entities;
   - whether third-party profiles are treated as supporting profiles rather than the canonical identity.

## Ranking interpretation

A technical PASS means the site is internally coherent and crawlable. It does **not** guarantee position #1. Search engines independently determine rankings using crawl/index state, authority, links, user demand, freshness, entity confidence, and other signals.

For the exact invented/owned brand query `iambandobandz`, the success target is straightforward: the owned domain should become the dominant canonical entity result as indexing and authority accumulate.

## Failure handling

If automated verification fails:

1. Do not paper over the failure with a manual exception.
2. Identify whether the failure is source drift, build drift, deployment propagation, DNS, or CDN cache.
3. Compare the deployed artifact against the canonical registry.
4. Fix the source-of-truth registry/build path rather than hand-editing generated output.
5. Re-run PR CI, deploy, and post-deploy verification.

### 2026-08-25 initial live-verification incident

The first post-deploy verification after canonical identity PR #34 failed even though both PR CI and the custom Pages deployment build passed. The live domain served the raw repository homepage/portfolio and returned 404 for generated-only `identity.jsonld` and `/.well-known/iambandobandz.json`.

GitHub simultaneously emitted its built-in dynamic `pages build and deployment` workflow from `main`, proving that legacy branch publishing was active alongside the custom `Deploy IAMBANDOBANDZ` workflow. The remediation in PR #35 adds deterministic synchronization of search-critical generated output back into repository source so both publishing paths expose the same canonical identity contract.

Search-critical source synchronization covers:

- `index.html`
- `portfolio/index.html`
- `identity.jsonld`
- `.well-known/iambandobandz.json`
- `sitemap.xml`

This synchronization is a compatibility guard, not a replacement for the canonical registry/build pipeline.

## Merge/deployment receipt

Record after completion:

- PR number:
- merged commit SHA:
- deployment run ID:
- deployment conclusion:
- post-deploy verification run ID:
- verification conclusion:
- verification timestamp (UTC):
- Google canonical inspection status:
- Bing canonical inspection status:
- first observed branded-search position/date:
