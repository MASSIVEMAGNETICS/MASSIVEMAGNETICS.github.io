# 4. Formal Definitions and Proposed Metrics

## 4.1 Time Saved (TS)

> **TS = H_baseline - H_actual**  
> Direct human time no longer technically required for the same verified outcome.

TS is the familiar productivity-side quantity. It is necessary but insufficient.

## 4.2 Net Human Time Return (NHTR)

> **NHTR = T_avoided + T_automated + T_rework_avoided + T_future_reuse - (T_interaction + T_maintenance + T_coordination + T_recovery + T_attention_tax)**  
> All terms are measured in expected human-hours over a declared horizon.

NHTR asks whether a system genuinely reduces human time requirements after secondary costs are included. A positive NHTR can still fail to increase human autonomy if the saved time is institutionally recaptured.

## 4.3 Sovereign Time Return (STR)

> **STR = NHTR × σ**  
> σ ∈ [0,1] is the fraction of net returned time that remains under meaningful human control.

The sovereignty coefficient σ should not be inferred from a single self-report. A mature measure would combine schedule flexibility, stopability, alternatives, ownership, voluntariness, and ability to reallocate the surplus without penalty. Recent World Bank work on time-use agency demonstrates that flexibility over timing can provide information beyond total hours alone. [5]

## 4.4 Temporal Return on Investment (TROI)

> **TROI = Expected future STR / Present human time invested**  
> A project-level measure for prioritizing automation, documentation, infrastructure, and workflow redesign.

## 4.5 Temporal Debt (TD)

> **TD = Σₖ E[required future human hoursₖ] / (1 + rₜ)^k**  
> Expected future human effort created by current decisions, discounted by a temporal discount factor rₜ.

Examples include technical debt, recurring manual administration, fragile integrations, unresolved compliance work, poor documentation, lock-in, and unfinished projects that require future reconstruction. Temporal debt is not morally negative by definition: debt may be rational when it buys greater future capability. The point is to book it.

## 4.6 Value per Effective Human Hour

> **VEH = Durable verified benefit / EHT consumed**  
> A complementary efficiency measure. Benefit must be specified for the domain rather than collapsed into a universal utility score.

| Metric | What it detects | Failure it prevents |
|---|---|---|
| TS | Direct technical savings | Confusing faster execution with no improvement |
| NHTR | Net savings after system overhead | Ignoring maintenance, rework, coordination, and attention costs |
| STR | Net savings actually under human control | Calling recaptured labor “freedom” |
| TROI | Future sovereign time per present hour invested | Automating low-value work with poor leverage |
| Temporal Debt | Future human obligations created now | Treating maintenance-heavy systems as free |
| VEH | Durable value per effective human hour | Maximizing activity rather than benefit |

---

# 5. Human-Time Farming as a System Condition

The phrase "human-time farming" is useful only if it is narrower than "anything that takes time." Reading, parenting, music, exercise, conversation, play, and contemplation consume time but may be intrinsically valuable, voluntary, and chosen precisely because the experience itself is desired. A usable definition must focus on systematic capture and asymmetry.

> **WORKING DEFINITION:** A system exhibits human-time farming when it systematically captures human time, optimizes mechanisms that increase or prolong that capture, converts the captured time or resulting behavior into value, and creates a material asymmetry between the value/control retained by the human and the value/control captured by the operator.

## 5.1 Provisional Human-Time Farming Index (HTFI)

> **HTFI = C × O × Aᵥ × (1 - G)**  
> C = capture intensity; O = optimization intensity; Aᵥ = value/control asymmetry; G = agency-preservation score. All components normalized to [0,1].

HTFI is explicitly provisional. It should be rejected or revised if its components cannot be measured reliably or if it fails to predict outcomes such as regret, inability to stop, low value-return, hidden pressure, or time-allocation distortion better than simpler baselines.

## 5.2 Why duration is ambiguous

- Long use can indicate high value: a person may willingly spend hours on art, sport, or conversation.
- Long use can indicate friction: cancellation mazes, poor interfaces, administrative burden, or repeated errors.
- Long use can indicate compulsion or pressure: interface design may exploit defaults, asymmetrical disclosure, or behavioral vulnerabilities.
- Short use can be beneficial if it accomplishes the user's objective quickly; it can also be harmful if the system prematurely blocks access or transfers work elsewhere.

The FTC and international consumer-protection networks reported that a large share of examined subscription sites and apps used possible dark patterns, illustrating why raw interaction metrics cannot be assumed to represent voluntary benefit. [10]
