# Massive Magnetics Convergence Engine V0

Public, read-only prototype for turning the Massive Magnetics public repository estate into an evidence-bounded capability graph and deterministic build-candidate queue.

## Inputs

- GitHub public user repository metadata for `MASSIVEMAGNETICS`
- `/proof/ledger.json`
- `/frontier-radar/data/feed.json`
- `/audit/offer.json`
- `/network/offer.json`
- `/store/commerce.json`

## Computation

1. Fetch every currently public repository visible through the GitHub public user API, paginated in-browser.
2. Derive transparent capability labels from repository metadata plus a small explicit map for canonical architecture components.
3. Compute a bounded readiness heuristic from public metadata and evidence coverage.
4. Classify the estate into verified core, active system, research/prototype, fork/reference, shell, archived, or unclassified.
5. Score predefined multi-capability product assemblies.
6. Render the strongest candidate and every selected repository so the recommendation is inspectable.

The score is a prioritization heuristic. It is not proof of novelty, product-market fit, scientific validity, production reliability, patentability, revenue, or customer adoption.

## Authority boundary

The browser may read public data only. It has no GitHub token, no private-repository access, no write endpoint, no deployment authority, no merge authority, and no payment authority. The output is advisory and stops at a human build/defer/kill decision.

If the public portfolio scan or Proof Ledger cannot be loaded, candidate generation fails closed rather than substituting fabricated repository state.

## Frontier direction

V0 proves the public interaction model. A later governed version can replace metadata heuristics with a CI-generated signed portfolio snapshot from Shared Completion Fabric, then attach Truth Compiler evidence vectors and Chronos receipts without changing the public human-approval boundary.
