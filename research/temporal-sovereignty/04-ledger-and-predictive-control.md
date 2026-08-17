# 9. Temporal Ledger Architecture

The framework becomes useful only when it can be instrumented. A Temporal Ledger is an event-level accounting system that records how much human time a workflow consumes, what it produces, what future time it avoids, what liabilities it creates, and who controls any resulting surplus.

| Field group | Example fields |
|---|---|
| Identity | workflow_id, actor_id, tool_id, organization_id, time_horizon |
| Baseline | baseline_human_minutes, baseline_error_rate, baseline_outcome |
| Execution | human_minutes, machine_minutes, interruptions, handoffs, retries |
| Quality | verified_outcome, error_rate, rework_minutes, confidence |
| Future effects | future_minutes_avoided, expected_reuse_count, maintenance_minutes |
| Agency | stopability, alternatives, voluntariness, schedule_flexibility, ownership |
| Disposition | time_saved, time_returned, time_recaptured, recipient_of_surplus |
| Economics | revenue, cost, value_created, value_recipient |
| Provenance | evidence_refs, version, authorization, timestamp, replayability |

## 9.1 Accounting rules

1. Declare the counterfactual baseline before optimization whenever practical.
2. Measure verified outcomes, not activity volume.
3. Include rework, maintenance, coordination, and recovery time.
4. Distinguish optional additional work from required additional work.
5. Book future obligations as expected temporal debt.
6. Record who receives economic value and who controls saved time.
7. Preserve privacy through local-first or minimally necessary measurement; do not turn temporal accounting into continuous surveillance.
8. Publish uncertainty intervals when counterfactual time savings are estimated rather than directly measured.

---

# 10. Integration with Predictive Semantic Control Systems

The temporal framework emerged from a broader architecture in which semantic compression, evidence evaluation, action selection, completion, verification, and continuity are treated as organs of one control system. [12] Temporal sovereignty supplies a candidate human-centered objective for that architecture.

*Figure 3. Temporal sovereignty as an objective layered above evidence, action selection, completion, verification, continuity, and reusable knowledge.*

| Component | Temporal function |
|---|---|
| Semantic Codec | Reduce repeated representation and explanation cost while preserving required meaning. |
| Handle Engine | Reduce retrieval and reconstruction time through stable semantic addresses. |
| Truth Compiler | Reduce downstream time wasted on weak or fabricated premises. |
| Reality Lever | Select interventions with high causal effect per unit of human effort. |
| Completion Engine | Move open loops toward terminal states and reduce future attention debt. |
| Chronos / Continuity Ledger | Prevent repeated rediscovery; preserve provenance and replayable outcomes. |
| Ethica / Authority layer | Prevent time optimization from overriding agency, consent, safety, or legitimate human constraints. |
| Victor runtime | Coordinate the loop while optimizing for verified human benefit rather than interaction volume. |

> **CANDIDATE SYSTEM INVARIANT:** A human-centered autonomous system should seek to maximize verified, agency-adjusted human time return subject to truth, authorization, safety, ownership, and continuity constraints—not maximize engagement, token generation, autonomous action count, or raw task volume.
