# 11. Applications

## 11.1 AI products

- Report human minutes per verified outcome alongside latency and token cost.
- Measure supervision and correction burden over weeks, not only first-run speed.
- Compare user-controlled time return against organization-captured productivity surplus.
- Use temporal debt to evaluate vendor lock-in, maintenance burden, and brittle agent chains.

## 11.2 Workplaces

- Add surplus-disposition metrics to AI productivity studies.
- Distinguish voluntary reinvestment of saved time from quota expansion.
- Measure schedule flexibility and ability to reallocate time, not only hours worked.
- Evaluate whether shorter task times improve well-being, income, learning, or simply workload density.

## 11.3 Software engineering and operations

- Rank automations by TROI rather than novelty.
- Book technical debt in expected future human-hours as well as dollars.
- Treat documentation, tests, reproducibility, and state continuity as temporal-capital investments.
- Kill or archive projects whose expected future attention cost exceeds realistic value.

## 11.4 Creator economy and media

- Distinguish rented-platform engagement from owned audience relationships.
- Measure promotion time per owned subscriber, customer, or repeat listener.
- Avoid treating maximum dwell time as the universal product objective; art may be valuable because time spent is itself chosen experience.
- Use agency-preserving attention design: clear sponsorship, stopability, transparent recommendations, and accessible alternatives.

## 11.5 Public policy

National time-use statistics and well-being research already provide infrastructure for measuring how people spend time. [2]-[5] A future policy research program could add questions about technology-mediated time savings, ability to reallocate them, unpaid digital administration, AI supervision, and the ownership of productivity surplus. This paper does not propose a legal entitlement to time surplus; it proposes better measurement before normative policy choices are made.

---

# 12. Research Program and Falsification Tests

The framework should be treated as a research hypothesis, not a discovered law. Its constructs earn their place only if they predict or improve outcomes beyond simpler measures.

| Hypothesis | Prediction | Baseline / comparator | Kill criterion |
|---|---|---|---|
| H1: Temporal ranking | Projects ranked by TROI yield more terminal outcomes per human hour. | Expected value / urgency ranking. | No material improvement across preregistered portfolio trials. |
| H2: Continuity return | Provenance-preserving continuity reduces reconstruction time. | Search-only or transcript-only workflow. | No reduction in human reconstruction time or error. |
| H3: Surplus disposition | Productivity gains and STR diverge under different organizational policies. | Productivity metric alone. | STR adds no explanatory or predictive value. |
| H4: Agency-sensitive interfaces | Equal semantic outcomes can be achieved with higher agency and lower unnecessary capture. | Engagement-optimized interface. | Agency metric unreliable or benefit vanishes after controls. |
| H5: Temporal debt | Expected human-hour debt predicts maintenance burden and abandonment. | Dollar cost / issue count / LOC. | No incremental predictive power. |
| H6: Ownership / lock-in | Owner-controlled systems have higher long-run NHTR when switching and maintenance are included. | Cloud/vendor-managed alternatives. | Owner-controlled systems consistently perform worse after full accounting. |

## 12.1 Minimum viable experiment: automation time audit

1. Select 20 recurring workflows with stable baselines.
2. Observe baseline human minutes, error rate, completion rate, and outcome quality for at least 10 runs each.
3. Automate or AI-assist half using a preregistered prioritization rule; retain matched controls.
4. Measure direct human time, supervision, rework, maintenance, context switching, and future reuse for 30 days.
5. Survey schedule flexibility and whether saved time was discretionary, voluntarily reinvested, or mandatorily recaptured.
6. Calculate TS, NHTR, STR, TROI, and conventional productivity.
7. Test which metrics best predict satisfaction, continued adoption, quality, and measured reduction in future workload.

## 12.2 Minimum viable experiment: project portfolio

Randomize eligible backlog items into two prioritization schemes: conventional expected-value ranking versus temporal-leverage ranking. Compare completed terminal states, verified value, human hours, reopened tasks, and temporal debt after 30-90 days. This directly tests whether temporal accounting improves execution rather than merely redescribing it.

---

# 13. Risks, Failure Modes, and Ethical Boundaries

| Risk | Failure mode | Mitigation |
|---|---|---|
| Goodhart effects | Teams optimize reported "hours saved" while increasing hidden workload. | Audit secondary costs; measure STR and outcomes, not self-reported savings alone. |
| Surveillance | Temporal measurement becomes employee or consumer monitoring. | Data minimization, local-first collection, aggregation, consent, purpose limits. |
| Utility reductionism | Joy, care, art, and contemplation are misclassified as inefficiency. | Do not equate nonproductive time with waste; include agency and experienced value. |
| Counterfactual error | Baseline time is guessed inaccurately. | Preregister baselines; use repeated observations; publish uncertainty. |
| Automation illusion | Tool shifts work into debugging or coordination. | Book all supervision, retries, rework, and maintenance. |
| Unequal surplus capture | Productivity rises without gains to affected humans. | Report surplus disposition separately from productivity; avoid normative inference without evidence. |
| Semantic self-confirmation | New vocabulary explains everything after the fact. | Require out-of-sample prediction and simpler baselines for each construct. |
| Cognitive dependency | Short-run savings reduce long-run competence or resilience. | Include skill-retention and fallback costs in temporal debt where material. |

> **NON-NEGOTIABLE BOUNDARY:** Temporal optimization must not become a justification for coercing people into "efficient" lives. Sovereignty means increasing meaningful control over time, including the freedom to spend time on activities that are not economically productive.

---

# 14. Implementation Roadmap

| Phase | Deliverable | Success criterion |
|---|---|---|
| 0-30 days | Temporal Ledger v0.1 across existing workflows | At least 50 instrumented executions with credible baselines and secondary-cost fields. |
| 30-90 days | NHTR / STR validation study | Inter-rater and test-retest checks; sensitivity analysis; observed divergence between TS and STR in real workflows. |
| 3-6 months | Temporal Audit product + internal dashboard | Repeatable audit producing measured hours recovered, debt retired, and uncertainty ranges. |
| 6-12 months | Open benchmark + research preprint | Public dataset with privacy protections; preregistered comparisons against conventional metrics. |
| 12-24 months | Cross-organization replication | Independent replication across work, creator, household, and software contexts. |

## 14.1 Highest-leverage first implementation

Instrument systems that already exist rather than creating a new conceptual branch. Chronos / Completion Engine workflows are ideal because they already record events, outcomes, provenance, and lifecycle states. Add temporal fields, run the ledger for 30 days, and test whether the new variables change project decisions or reveal hidden negative-return automation.
