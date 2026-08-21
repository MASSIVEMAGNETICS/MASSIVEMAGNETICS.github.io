# Frontier Radar V1.2 Threat Model

## Security objective

Treat every upstream field as hostile data while keeping the scanner useful during partial outages. The system must not convert public-source intelligence collection into arbitrary web access or private surveillance.

## Trust boundaries

| Boundary | Trusted | Untrusted |
|---|---|---|
| Scanner code | repository-reviewed Python | remote API payloads |
| Network | fixed HTTPS endpoints | redirects, response bodies, rate-limit errors |
| Feed | validator-approved committed snapshot | candidate scan before quality gate |
| Browser | local static JS/CSS | feed strings and outbound source URLs |
| Deployment | GitHub Pages workflow | upstream source availability |

## Threats and mitigations

### Upstream payload injection

**Threat:** titles, summaries, authors, tags, or URLs contain HTML/script payloads.

**Mitigations:**
- control-character stripping and length caps,
- source-specific HTTPS host allowlists,
- browser rendering through DOM text nodes rather than `innerHTML`,
- restrictive Content Security Policy,
- external links use `noopener noreferrer`.

### SSRF / malicious redirects

**Threat:** an upstream redirect or malformed URL causes the scanner to request an arbitrary host or leak a GitHub token.

**Mitigations:**
- scanner APIs are fixed and HTTPS-only,
- redirect destinations are revalidated against an API host allowlist,
- `Authorization` is removed if a redirect changes host,
- item URLs are validated against source-specific host allowlists.

### Resource exhaustion

**Threat:** oversized API response, repeated transient failures, or runaway retries consume Actions time/memory.

**Mitigations:**
- 5 MiB response cap,
- 20 second request timeout,
- bounded retry count,
- exponential backoff / `Retry-After` support,
- fixed query count and result limits.

### Poisoned or low-quality snapshot

**Threat:** partial outage or manipulated source yields an empty/misleading feed that replaces good data.

**Mitigations:**
- per-source request/success accounting,
- source considered healthy only after majority request success and nonzero data,
- minimum healthy-source and item floors,
- failed candidates cannot overwrite last-known-good `feed.json`.

### Feed tampering

**Threat:** feed changes in transit or an accidental edit corrupts the dashboard.

**Mitigations:**
- observation and ranking hashes per item,
- canonical feed hash,
- exact file SHA-256 sidecar,
- status/feed hash cross-check,
- browser verifies byte digest before parsing/rendering.

**Residual risk:** hashes are integrity receipts, not a secret-key signature. Repository permissions and Git history remain the authenticity trust anchor.

### CI/CD compromise

**Threat:** workflow permissions allow unnecessary mutation or Pages deployment rights.

**Mitigations:**
- refresh and deploy are separate workflows,
- refresh receives only `contents: write`,
- deploy receives only `contents: read`, `pages: write`, `id-token: write`,
- deployment consumes committed snapshots instead of requiring live external APIs,
- Dependabot monitors GitHub Actions dependencies.

### False positives / ranking manipulation

**Threat:** stars, forks, downloads, or keyword stuffing inflate rank.

**Mitigations:**
- logarithmic traction scaling,
- traction is only 12% of the score,
- reproducibility and frontier relevance are separate dimensions,
- velocity uses nonnegative observed deltas,
- ranking components are displayed publicly.

**Residual risk:** metrics can still be gamed. High radar rank means "inspect this," not "believe this."

## Privacy boundary

The radar is intentionally limited to public technical artifacts. It does not collect private communications, private repositories, device identifiers, location histories, or credentials.

## Incident behavior

If snapshot validation fails, preserve the previous feed, mark status unhealthy for the candidate run, and fail the refresh workflow. Do not publish an unvalidated replacement.
