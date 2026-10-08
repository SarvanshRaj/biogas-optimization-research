# Disconfirmation reviews: Phase 2

**Label:** INTERNAL · **Date:** 2026-10-07 · **Status:** complete for Phase 2.
**What this document is, honestly.** These are **structured self-critiques from named standpoints** written by
the agent, not interviews with real practitioners, operators or statisticians. No human was consulted. They are
an adversarial *procedure*, the point is to force the specification to answer objections it would otherwise
never hear, and they are **not evidence** about the world. Where a standpoint rests on retrieved sources, the
citation is given; where it rests on general reasoning, it says so.
**No winner is chosen here:** this document does not rank the lenses or issue recommendations. The
disagreements are mapped, and the conflict map that decides between them is a Phase 4 deliverable.

---

## Lens 1: The practitioner (household / small-farm operator, India)

**Core position.** "Your model's knobs are not my knobs. I can choose what goes in the drum, how much water I
add, where the drum sits (temperature), how often I feed it and whether I let it sit before feeding. I cannot
measure pH to 0.1, I cannot set an OLR in kg VS per m³ per day, and I cannot control an inoculum ratio. If your
optimiser recommends a hydraulic retention time of 28 days; that is not advice, it is a laboratory parameter
written in household clothing."

**Strongest evidence it can cite.** The retrieved practice layer consistently names *temperature*, *gas
tightness* and *winter standstill* as the binding problems, not pH control (CIT-0024, CIT-0025, CIT-0026,
CIT-0027). Official and review sources describe India's installed base as cattle-dung systems of 1–10 m³/day
(CIT-0029, CIT-0030), i.e. a different feedstock regime from food waste. The Indian hotel-waste study had to use
a laboratory batch reactor at 37 °C to measure anything at all (CIT-0028).

**Unique message.** *Tier your decision variables by who can actually set them, report the optimiser's advice
separately per tier, and never let a laboratory-only variable appear in a "recommended recipe".*

**What would change its mind.** Evidence that household operators routinely monitor pH or control loading
rates, none was retrieved.

**What the specification did.** **Accepted**: decision **S-7**: every input is tiered C1 (controllable),
C2 (laboratory-only) or C3 (observed), and the optimiser runs twice (C1∪C2, and C1 only) with both results
reported and labelled.

---

## Lens 2: The sceptic (of this project)

**Core position.** "You wrote an equation, then you will train five models to recover your own equation, then
you will 'optimise' your own opinions and present the result as an optimisation study. The biological premise is
weaker than the software is clever: the literature you retrieved does not contain the study your concept
requires, food waste is already highly degradable, and fungal pre-treatment's sign is not even stable across
strains. Strip away the machine learning and what is left is a sensitivity analysis of your own assumptions."

**Strongest evidence it can cite.** No retrieved study applies pure *A. oryzae* to food waste and then digests
that same waste (Phase 1 §2.4); an opened review carries explicit null and negative findings for fungal
pre-treatment (CIT-0009); food waste reaches ~81 % VS destruction untreated (CIT-0003); real-world models do not
transfer between digesters (CIT-0023).

**Unique message.** *The deliverable is a **method**: a reproducible, honestly-bounded pipeline, not a result
about biogas. Report it that way, or the project is overclaiming.*

**What would change its mind.** A held-out empirical BMP dataset against which the pipeline could be tested.
None is available in this project (simulation-only), so the sceptic's position cannot be defeated here, only
contained.

**What the specification did.** **Accepted in framing, not in structure**: the specification keeps the
simulator (the project's brief mandates it) but adds three containers: the true-vs-surrogate gap as the headline
optimisation metric (S-8), the permuted-target negative control (S-10), and an explicit
"what this specification does not do" section (§13). The report must state that no claim about real digesters is
made. **Unresolved disagreement:** the sceptic would delete Stage 1 entirely; the brief requires it, so it stays
as an explicitly-assumed, sign-symmetric factor.

---

## Lens 3: The data scientist

**Core position.** "The design has three leak risks and one interpretability trap. (1) Latent factors that
determine the target must never appear as features, you handled that. (2) Rounding inputs creates
near-duplicate rows; if the split were row-wise, replicates would straddle train/test and R² would be
inflated, the scenario-grouped split handles it, but only if a test *asserts* it rather than assuming it.
(3) The generator is smooth and mostly multiplicative; if it turns out to be effectively additive, Ridge will
match the trees and the five-model comparison will be an expensive way to learn nothing. And the trap: feature
importance from a model trained on your own equation will be read by someone as biology."

**Strongest evidence it can cite.** Retrieval-level: real full-scale attempts needed 150–200 samples for stable
prediction and still failed to transfer across digesters (CIT-0023); a 100-sample study is typical in this
literature (CIT-0022). Method-level: this is general machine-learning practice, not a retrieved claim.

**Unique message.** *Pre-declare the uninformative case (F3) and add a negative control, or the model
comparison will be reported with more confidence than it deserves.*

**What would change its mind.** A simulator whose interaction structure is strong enough that trees beat Ridge
decisively on held-out data, which is exactly what F3 tests.

**What the specification did.** **Accepted**: S-5 (declared noise structure), S-10 (permuted-target control +
duplicate-row guard), S-9 (OOD family), and the F3 rule written into §9.1 so that "Ridge ≈ trees" produces an
*uninformative* verdict rather than a headline. **Partial disagreement kept:** the DS lens wanted the
composition collinearity (r ≈ −0.5) removed by re-parameterising to two independent axes; the specification
keeps all three fractions because they carry the mechanism, and instead forbids causal readings of their
importances.

---

## Lens 4: Operations and economics

**Core position.** "There are no costs in your model, so your optimiser will walk to a corner: maximum lipid,
longest pre-treatment, best temperature, and it will call that optimal. Heating is the largest energy cost in a
real small digester; pre-treatment costs days of throughput; adding water to reach a low solids content means a
bigger vessel. A zero-cost optimum is not an optimum, it is a boundary."

**Strongest evidence it can cite.** The practitioner layer names winter temperature collapse and the cost of
getting heat into the system (CIT-0025, CIT-0026); the Indian policy literature's barriers are economic and
maintenance-related (CIT-0030).

**Unique message.** *If you cannot model costs, then at minimum attach a cost proxy to the recommendation and
show the trade-off frontier instead of a single "best" point.*

**What would change its mind.** Real cost data for household-scale digesters in this setting, out of scope
here, since it would require claims this project cannot support.

**What the specification did.** **Partially accepted.** The optimiser stays cost-free (the brief says optimise
only the simulator-defined outcome), but the specification freezes reported **resource proxies** at analysis
time: heating demand proxy (∝ temperature above ambient × slurry mass), pre-treatment duration in hours, and
water added to reach the chosen total solids. These are labelled **proxies with no economic calibration** and
are never optimised. **Disagreement kept:** the operations lens wants them inside the objective; the
specification refuses, because that would change the objective the brief fixed.

---

## Lens 5: Academic methods

**Core position.** "Four methodological holes. (1) You updated a prior in Phase 1 without any stated update
rule, 0.30 → 0.40 is a number pulled by hand. (2) Your sensitivity ranges are honest labels, but the
**distribution** of the latent factors is not declared anywhere, so 'sensitivity analysis' could mean anything
later. (3) The calibration of β leans on a single measured study. (4) Your anchors table is arithmetic you ran
yourself before freezing, good practice, but it must be labelled as specification validation, not as results."

**Strongest evidence it can cite.** The Phase 1 artefacts themselves: the prior table in
`docs/literature_review.md` §8 moves three priors with no rule; the parameter table lists ranges but not the
sampling distributions; the calibration anchor is one study (CIT-0003).

**Unique message.** *Pre-declare the sweep grid and the prior-update rule **now**, or Phase 4's "sensitivity
analysis" will be whatever turned out to be interesting.*

**What would change its mind.** Seeing the grid and the rule fixed before code, which is what this phase
delivers.

**What the specification did.** **Accepted**: S-12 (a ten-item sweep grid with levels, §14 of the spec),
S-13 (prior-update rule with per-tier caps, addendum 03 §A3.5), declared latent distributions (§3.1), and the
anchors explicitly labelled "specification-validation arithmetic, not project code and not a data generation".
**Retained criticism:** β remains calibrated against a single anchor study; the spec answers this by sweeping β
and by stating the upper-tail caveat rather than by pretending one study settles the scale.

---

## Lens 6: The historian (long view)

**Core position.** "Biogas-from-waste is a nineteenth-century idea that has been re-pitched roughly every
generation. The recurring pattern is not microbiological failure but **maintenance failure**: plants are
abandoned, not out-competed. India's own programme has run since 1981-82 with millions of installations; the
interesting questions in that archive are about feedstock switching, subsidy design and repair, none of which
your simulation can address. Also: the 'add an enzyme/fungus and get more gas' claim is old, and its record on
already-degradable waste is unimpressive."

**Strongest evidence it can cite.** The MNRE FAQ (programme since 1981-82; 4.31 million plants installed
against ~12 million potential; an evaluation reporting 95.81 % operational) and the barriers review (production
2.07 against a 29–48 billion m³/year potential), both context-tier, both *institutional*, not experimental
(CIT-0029, CIT-0030). The fermentation/pretreatment literature's mixed record (CIT-0009, CIT-0018, CIT-0032).

**Unique message.** *The sociological and economic failure modes dominate; a biochemical simulation is a
legitimate but narrow instrument, and the report should say which questions it cannot touch.*

**What would change its mind.** Adoption data showing feedstock switching from dung to food waste at
household scale, not retrieved, and out of scope.

**What the specification did.** **Accepted as scope boundary**: §13 of the spec states that contaminants,
economics, maintenance and adoption are out of scope; the limitations section of the report must carry the
historian's point explicitly, and no recommendation may be phrased as an adoption claim.

---

## Disagreement map (no winner chosen)

| # | Disagreement | Positions | Where it stands after Phase 2 |
|---|---|---|---|
| M-1 | Should laboratory-only variables be part of the recommendation? | Practitioner: no. DS: they are needed to test the learners. | **Adopted the practitioner's form**: both tiers reported separately (S-7). The *ranking* consequence is deferred to the Phase 4 conflict map. |
| M-2 | Should costs enter the objective? | Operations: yes. Brief + spec: no. | Objective frozen cost-free; cost *proxies* reported (never optimised). Unresolved by design. **Phase-4 close:** closed as declared, the objective is already artefactual under F5, so a second unvalidated quantity is not added; `conflict_map.md` §C. |
| M-3 | Is the model comparison informative at all? | Sceptic: no, it is self-referential. DS: it is informative *if* nonlinearity is real, which is testable. | **Deferred to F3** with a pre-declared verdict rule. Not decided by argument, decided by the Phase 4 result. **Phase-4 close:** F3 does not fire (Ridge 55.9 % of the booster's R²) and F7 does not fire → informative about the simulator's *structure*, not about recommending (F5 fires) and not about real digesters; `conflict_map.md` §C. |
| M-4 | Should composition collinearity be removed by re-parameterisation? | DS: yes. Spec: no (mechanism), with causal-reading ban. | Recorded as a retained criticism; the sensitivity grid is where it can be revisited. |
| M-5 | Is Stage 1 worth modelling given the weak evidence? | Sceptic: delete it. Brief: it is the study's subject. | Stage 1 stays, as an explicitly-assumed sign-symmetric factor; the pre-registered F1 already governs its interpretation. **Phase-4 close:** the sweep shows the factor moves the level (±8–10 %) and the recommendation **0.0 %** → the model cannot rank on it, and no Stage-1 conclusion is drawn; `conflict_map.md` §C. |
| M-6 | Does a biochemical simulation speak to the real failure modes? | Historian/practitioner: mostly not. Academic: it can, if bounded honestly. | Everyone agrees it must be **bounded honestly**; the disagreement is about how much of the report that leaves. Phase 5's tiering (A/B/C) is where it gets settled. |

---

## Hostile re-read of the plan and the evidence documents

Performed against a deliberately unsympathetic question: *"where is this document claiming more than it
knows?"* Findings are listed with the action taken. Three were real; two were cosmetic.

| # | Finding | Severity | Action |
|---|---|---|---|
| H-1 | `docs/parameter_table.md` used the status code `V-FULL` for CIT-0028 while the ledger recorded `open_full_text_partial`, the +41 % figure comes from the paper's **abstract**, since the results section was never read. | **Real, traceability** | Fixed: the status-code definition now carries the caveat explicitly. |
| H-2 | The composition sampling box declared in Phase 2's first draft was **nearly infeasible** (37.5 % acceptance) and silently drove the simulated feedstock lipid-rich (mean 0.22). A defect that would have biased the whole study toward inhibition-heavy regimes. | **Real, design** | Fixed before any code: decision S-6 and addendum 03 §A3.3 record before/after numbers. |
| H-3 | The prior-update rule did not exist when a prior was moved; the movement sat exactly at the cap the later rule would have imposed. | **Real, method** | Rule declared (S-13) with an explicit retrospective check recorded in addendum 03 §A3.5, rather than quietly retro-fitting. |
| H-4 | CIT-0009's "25–120 %" range was seen in the article's indexed text, not in a line-by-line full read. | Cosmetic (the ledger already said the article was read at that level) | Ledger note now states it explicitly. |
| H-5 | The first author of CIT-0007 was transcribed without the rest of the author list. | Cosmetic (metadata was Crossref-verified) | Ledger note now carries a Phase 5 pre-publication re-check requirement. |

**What the hostile re-read did not find:** no unsupported numeric claim resting on an invented source; no
injection obeyed; no claim in Phase 0–1 documents that contradicts the ledger; no hidden change to the locked
pre-registration (its hash still verifies).

---

## What Phase 2 does *not* claim

1. These lenses are **not** interviews or surveys; they are role-structured self-critique, and no human was
   consulted.
2. The specification is **not** validated against reality. Its calibration anchors are arithmetic checks
   against one measured study (CIT-0003) and are labelled as such.
3. The disagreement map deliberately leaves M-2, M-3 and M-5 **open**; Phase 4's conflict map, not this
   document, is where they are decided. *(Phase-4 close: `docs/contradictions.md` §C has now done
   that, on measured evidence, and carries M-6 to Phase 5. The rows above are annotated in place; the
   Phase-2 argument is unchanged.)*
