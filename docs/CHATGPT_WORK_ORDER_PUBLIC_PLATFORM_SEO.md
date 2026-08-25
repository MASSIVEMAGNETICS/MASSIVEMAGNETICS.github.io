# ChatGPT Work Order — iambandobandz Public Platform + Search Identity

**Work order ID:** IBB-WO-2026-08-24-SEO-PLATFORM-01  
**Canonical brand:** `iambandobandz`  
**Canonical domain:** `https://iambandobandz.com/`  
**Repository:** `MASSIVEMAGNETICS/MASSIVEMAGNETICS.github.io`  
**Owner approval:** Approved in conversation on 2026-08-24  
**Execution rule:** Preserve working revenue paths. Do not publish fake or nonfunctional Radio/Community routes merely to satisfy navigation design.

## Objective

Convert the existing public site from a collection of strong static surfaces into a coherent, canonical owned-platform foundation while maximizing legitimate branded-search discoverability for the query `iambandobandz`.

The technical target is to make every machine-readable signal consistently resolve:

`iambandobandz` → `https://iambandobandz.com/`

No technical implementation can guarantee a #1 position on Google, Bing, Brave, DuckDuckGo, or another search engine. Ranking is controlled by each search engine. This work order maximizes the signals under owner control and creates deterministic verification so identity drift is caught before deployment.

## Canonical identity contract

1. The canonical artist/brand token is exactly `iambandobandz`.
2. `IAMBANDOBANDZ` may be used only as visual presentation/case styling.
3. `Bando Bandz` must not be emitted as a machine-readable artist alias.
4. The canonical owned web origin is `https://iambandobandz.com/`.
5. B Heard Network's owned canonical route is `https://iambandobandz.com/network/`.
6. The active direct store canonical route is `https://iambandobandz.com/store/`.
7. The public site must expose one internally consistent JSON-LD entity graph, sitemap, web manifest, robots declaration, well-known identity manifest, and LLM-readable identity file.
8. Owner-only/local control surfaces remain excluded from search-oriented routing. Robots directives are not treated as an authentication boundary.

## Current architecture to preserve

The public site remains a GitHub Pages deployment backed by a canonical registry and deterministic build step.

```text
iambandobandz.com
│
├── Artist / catalog / direct store
├── B Heard Network creator infrastructure
├── Truth Compiler
├── Proof Ledger
├── Research Registry
├── Frontier Radar
├── Signal experiment
└── Massive Magnetics portfolio
```

The next platform layer is planned as:

```text
ATTENTION
   ↓
B HEARD RADIO          ← recurring reason to return
   ↓
B HEARD ID             ← owned identity
   ↓
COMMUNITY              ← relationship
   ↓
STORE / SERVICES       ← monetization
```

`/radio/`, `/community/`, and `/login/` are reserved architecture targets. They must not enter the indexable sitemap until functional acceptance criteria are met.

## Phase A — canonical search/identity hardening

### A1. Registry normalization

- Set the artist entity name to `iambandobandz`.
- Remove `Bando Bandz` from artist aliases.
- Preserve `Bando` only as a person-level alias where useful.
- Set B Heard Network's canonical URL to the owned `/network/` route.
- Mark the existing `/store/` route as the active canonical store.
- Set the WebSite entity name to `iambandobandz`.
- Add a canonical brand field to the public profile.

### A2. Structured data

Generate JSON-LD from the canonical registry, not hand-maintained page fragments.

Required graph nodes:

- `Person` — Brandon Emery
- `MusicGroup` — `iambandobandz`
- `WebSite` — `iambandobandz`
- `Organization` — B Heard Network
- `Organization` — Massive Magnetics
- active supporting software/site entities

Requirements:

- one canonical artist node;
- exact owned URL;
- verified `sameAs` platform links only;
- no conflicting artist alias;
- WebSite `about` relationship points to the canonical artist entity;
- generated graph is also published as `/identity.jsonld`.

### A3. Homepage search contract

The built homepage must:

- lead the `<title>` with `iambandobandz`;
- use an exact canonical link to `https://iambandobandz.com/`;
- use `iambandobandz` as Open Graph site name;
- remove obsolete `meta keywords`;
- remove the spaced legacy phrase `I AM BANDO BANDZ` from search-visible source;
- prioritize current working music/store/creator paths over the technical audit in global consumer navigation;
- preserve Truth Compiler as a working revenue path elsewhere on the page.

### A4. Search discovery files

Maintain and verify:

- `/robots.txt`
- `/sitemap.xml`
- `/site.webmanifest`
- `/identity.jsonld`
- `/.well-known/iambandobandz.json`
- `/llms.txt`
- `/registry/public/identity.json`
- `/registry/public/entities.json`

The XML sitemap must be generated from the canonical route registry during deployment. The committed source sitemap should remain synchronized for repository readability.

### A5. Route/canonical repair

Indexable deployed routes must use `iambandobandz.com` canonical URLs. In particular:

- repair portfolio canonical URL and remove external `chatgpt.site` social metadata dependency in the built artifact;
- add an explicit canonical URL to Frontier Radar;
- include currently deployed indexable surfaces in the sitemap;
- exclude `/owner/` and other private/local control surfaces from the search-route registry.

## Phase B — verification infrastructure

### B1. Pull-request gate

Every PR touching the site must be able to run:

1. canonical registry validation;
2. complete Python unit tests;
3. sanitized site build;
4. built-site registry validation;
5. checks that critical search artifacts exist;
6. checks that the legacy artist alias is absent from the built homepage.

### B2. Post-deploy verification

After the production Pages workflow completes successfully, run a live verification job against `https://iambandobandz.com/`.

Verify:

- homepage 200 response;
- canonical title/link/OG identity;
- no legacy artist alias leakage;
- robots advertises the canonical sitemap;
- sitemap contains all approved indexable routes;
- web manifest resolves to `iambandobandz`;
- JSON-LD contains exactly one canonical MusicGroup node;
- well-known identity manifest agrees with the registry;
- `llms.txt` declares the canonical artist and domain;
- portfolio canonical is repaired;
- Frontier Radar canonical is present.

The verifier must retry briefly to tolerate CDN/Pages propagation after deployment.

## Phase C — public platform information architecture

Do not create dead links. Implement this phase when the corresponding functionality exists.

Target global hierarchy:

```text
RADIO
COMMUNITY
MUSIC
STORE
CREATORS
PROOF
LAB
```

Target platform ownership model:

- `iambandobandz` = attraction / artist signal
- B Heard Radio = retention
- B Heard ID = identity ownership
- Community = relationship
- Store + creator services = monetization
- Massive Magnetics = technical leverage
- Proof = credibility

## Phase D — B Heard ID / dynamic backend

Use an authenticated backend rather than attempting to turn GitHub Pages itself into an auth server.

Preferred zero-cost MVP architecture:

```text
GitHub Pages frontend
        ↓
Supabase Auth + Postgres + RLS
        ↓
profiles / posts / comments / follows / reports / moderation
```

Security requirements:

- no service-role/admin secret in client JavaScript;
- authorization enforced in database RLS, not by hidden buttons;
- owner/admin roles verified server-side;
- current local encrypted `/owner/` vault is not treated as remote authentication;
- explicit consent and retention rules for member data;
- audit log for moderator/admin mutations.

## Phase E — B Heard Radio

Target architecture:

```text
local radio/programming engine
        ↓
YouTube Live distribution
        ↓
custom B Heard web player
        ↓
member identity / favorites / follows / requests / commerce
```

V1 acceptance criteria:

- public custom B Heard wrapper;
- official YouTube playback path underneath where appropriate;
- now-playing metadata;
- artwork;
- current artist/track;
- request action;
- share action;
- join/login action when B Heard ID is live;
- no VLC dependency in the customer-facing product.

Do not add `/radio/` to the sitemap until it is a functional public experience.

## Search-engine operations outside the repository

After deployment, owner-controlled webmaster consoles should be used to accelerate discovery where available:

- submit/refresh the canonical sitemap in Google Search Console;
- submit/refresh the canonical sitemap in Bing Webmaster Tools;
- inspect the canonical homepage URL after deployment;
- request indexing only after canonical/meta/structured-data verification passes;
- monitor branded query results for `iambandobandz` over time.

Do not manufacture backlinks, fake traffic, keyword stuffing, hidden text, doorway pages, or automated search clicks. These create ranking and account risk and are not part of this work order.

## Merge gate

A PR may merge only when:

- source registry validation passes;
- all unit tests pass;
- sanitized site build succeeds;
- built-site validation passes;
- PR search-contract CI passes;
- diff contains no unexpected deletion of revenue routes;
- canonical brand is `iambandobandz` everywhere machine-readable;
- no new indexable route points to a nonfunctional page.

After merge, the production deployment must complete and the post-deploy public verifier must pass.

## Success metrics

### Immediate technical success

- zero canonical-domain conflicts in deployed HTML;
- zero `Bando Bandz` artist aliases in generated structured data;
- sitemap and registry agree exactly;
- all indexable routes resolve on the canonical domain;
- live post-deploy verifier passes.

### Search success observed over time

- `iambandobandz.com` is indexed for the branded query `iambandobandz`;
- the owned domain becomes the dominant canonical result for that exact brand query;
- sitelinks/secondary results increasingly resolve to owned routes rather than fragmented third-party profiles;
- third-party music/social profiles remain linked as supporting `sameAs` evidence rather than competing canonical origins.

## Non-goals for this PR

- pretending a search ranking can be guaranteed;
- shipping fake Radio/Community pages;
- implementing Supabase before project credentials/configuration are authorized;
- changing the current owner vault into a fake authentication system;
- hosting user-uploaded video;
- rebuilding YouTube distribution;
- breaking existing Stripe/revenue routes while reorganizing navigation.
