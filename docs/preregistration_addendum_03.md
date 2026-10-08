# Pre-registration addendum 03, specification decisions

**Label:** INTERNAL · **Date:** 2026-10-07 · **Status:** active · **Recorded:** at the end of Phase 2,
**before** any project code exists (`src/` and `tests/` are still empty).
**Relationship to the lock:** `docs/preregistration.md` is not edited. This addendum records (a) the decisions
that froze the model specification, (b) one labelling correction, and (c) one pre-code design correction found
by the Phase 2 checks.

---

## A3.1 Labelling correction: the specification decisions are renamed **S-\*** (not D-\*)

The Phase 1 addendum used **D8 / D9 / D10** for the endpoint-window, inoculum-basis and
contradiction-carried decisions. They collided with the **D-series** used here for user-level decisions, which is a
different decision register, and with the parameter-table rows **D1–D8**. A number that means three things is a
traceability defect, so the specification decisions are renamed:

| Old label | New label | Content (unchanged) |
|---|---|---|
| D8 | **S-1** | Primary target = endpoint yield over a declared 30-day window; pre-treatment split into availability gain and degradable-mass loss |
| D9 | **S-3** | Inoculum ratio declares its basis (g VS inoculum per g VS substrate) |
| D10 | **S-4** | The total-solids contradiction is carried live (claim C-005), not averaged away |

**This is a labelling change only**: no decision content changed. `docs/preregistration_addendum_02.md` was
edited to use the new labels; its hash therefore changed from
`10b60934517ad8f8f36afc16cd27844595f56f3905ad4b53f5f14067b8cad031` to
`f56eff066cb826d239dad8b7a6456dd8d7ebcd784398387226723abcaf19096f`. Both hashes are recorded in
`docs/notebook/prereg_v1.md`, so the edit is visible rather than silent.

---

## A3.2 The specification decisions (all recorded before code)

| # | Decision | Rationale | Forced by |
|---|---|---|---|
| **S-1** | Endpoint yield over a declared **30-day** window; pre-treatment = availability gain × (1 − mass loss) | The literature reports pre-treatment effects on *rate* at least as often as on potential (C-004); a target must therefore say *when* it is measured | Phase 1 evidence (CIT-0016) |
| **S-2** | Pre-treatment acts on **both** the ceiling and the rate (the only factor allowed to act twice, deliberately) | Makes the rate-versus-extent distinction visible in the output instead of hidden in an assumption | Sceptic + academic lenses |
| **S-3** | Inoculum ratio basis declared; no sourced optimum claimed | Two conventions coexist in the sources (VDI 4630 vs 1:1) | Phase 1 (CIT-0004) |
| **S-4** | The TS-direction contradiction is carried as a live claim with three pre-declared shape variants in the sensitivity grid | The two retrieved studies disagree (C-005); averaging them would invent a fact | Phase 1 evidence |
| **S-5** | Noise = scenario-level effect (σ 0.04) + replicate-level effect (σ 0.05), plus input rounding and 2 %/1.5 % missingness | Visible noise that the grouped split can contain; missingness gives the leakage guards something to catch | Data-science lens |
| **S-6** | Composition sampled from a **declared distribution**, carbohydrate band narrowed to 0.45–0.74 | The uniform box over the old band is nearly infeasible under the simplex constraint, see A3.3 | Design check (found a real defect) |
| **S-7** | Every input is tiered **C1 controllable / C2 laboratory-only / C3 observed**, and the optimiser is run twice (C1∪C2 and C1 only) | Most "decision variables" are not controllable by the person the project is for | Practitioner lens |
| **S-8** | Optimiser has three arms, true-objective (oracle), surrogate-with-true-re-evaluation, and baseline, and the **gap between arms 1 and 2 is the headline metric** | In a synthetic study the only honest way to talk about an optimiser is to measure how much of its apparent gain is exploitation of the surrogate | Sceptic + DS lenses |
| **S-9** | OOD family defined as lipid 0.30–0.38 **and** TS 22–28 %, 60 scenarios, never used for fitting | A real extrapolation test needs to leave the support without collapsing to zeros | DS lens |
| **S-10** | Pre-declared **permuted-target negative control** and duplicate-row guard | Proves the pipeline cannot manufacture skill from noise | DS lens |
| **S-11** | Constraints frozen: sum-to-one by parameterisation, hard ranges, stability ≤ 0.35, TAN ≤ 4.0 g/L, pH_eff ∈ [6.5, 8.5], HRT ≥ 12 d | Feasibility must go beyond yield, and the thresholds must exist before the optimiser is run | Operations lens |
| **S-12** | Sensitivity grid frozen (10 assumptions × 3 levels, §14 of the spec) | Otherwise the "sensitivity analysis" would be chosen after seeing what is fragile | Academic lens |
| **S-13** | Prior-update rule declared (see A3.5) | Phase 1 moved a prior without a stated rule | Academic lens |

---

## A3.3 Design correction found by the Phase 2 checks (S-6), before/after

The first version of the sampling design drew composition uniformly over `c ∈ [0.30, 0.70]`,
`p ∈ [0.05, 0.25]`, `l = 1 − c − p`. The design check revealed that this box is **nearly infeasible**: the
simplex constraint requires `c + p ≥ 0.70` for `l ≤ 0.30`, so

| | before (uniform box) | after (declared distribution) |
|---|---|---|
| acceptance rate | **37.5 %** | **64 %** |
| surviving lipid distribution | mean **0.22**, min 0.055, forced lipid-rich | mean **0.18**, median 0.18, p05 0.11, p95 0.27 |
| carbohydrate band | 0.30–0.70 (mean 0.50 after rejection) | **0.45–0.74**, mode 0.65 (inside the sourced 12–74 % spread) |
| structural correlations | r(c,l) = −0.73 | r(p,l) = −0.55, r(c,p) = −0.48, r(c,l) = −0.48 |

The replacement keeps every value inside the sourced ranges, produces a lipid-typical food-waste distribution,
and removes the accidental push toward lipid-rich feed. **No results were affected: no simulator existed yet.**
This is recorded as a pre-code correction, not as an AD_HOC change after results.

**Effect on R-E2 (the deferred redundancy test):** resolved at design level. Across the 11 variables the
largest absolute correlation is 0.55 (the structural composition pair). Excluding composition pairs the largest
is **0.057**; specifically r(OLR, TS) = +0.035, r(I:S, OLR) = −0.002, r(HRT, OLR) = +0.027. OLR/TS and I:S/OLR
are therefore non-redundant **by construction**, and the composition collinearity is documented as a
limitation on feature-importance interpretation.

---

## A3.4 The Phase 3 gate, what may and may not happen next

1. Phase 3 implements **exactly** `docs/model_specification.md` (SPEC_V1). Every constant, equation, column,
   split rule, constraint and sweep level is taken from that document.
2. Phase 3 may **not** add a variable, a factor or a model. Adding a sixth model is a change to a frozen
   protocol and would void the pre-registration.
3. If implementation reveals that a specified equation cannot be computed as written (for example a numerical
   problem), the fix is an **AD_HOC** entry in `docs/notebook/phase_log.md` with before/after results, never a
   silent edit.
4. Tests are written **before** the code they test (RED→GREEN→REFACTOR), with RED evidence recorded in
   `docs/notebook/test_log.md`. A test written after its implementation is not evidence and must be labelled as
   such.

---

## A3.5 Prior-update rule (declared now, applied prospectively)

Priors move only by a stated rule, and every movement is logged with its source:

| Evidence tier | Maximum movement per source |
|---|---|
| Direct study, **same substrate and the organism named** | ± 0.10 |
| Direct study, same substrate, different agent/organism | ± 0.05 |
| Analogous substrate or system | ± 0.02 |
| Review, context, UGC | ± 0.01 |

Additional rules: movements accumulate only from **independent** sources; a null or negative finding may move a
prior downward by the same caps; and no rule permits moving a prior more than once on the same source.

**Retrospective check on Phase 1 (recorded because the rule post-dates the movement it judges):** P-A moved
0.30 → 0.40, i.e. +0.10, justified by CIT-0007, a direct food-waste pre-treatment study that **names
*Aspergillus oryzae***. Under the rule as written this is the maximum permitted single-source movement, so the
Phase 1 update is compliant, but it sits at the **cap**, not comfortably inside it. Under the rule, a further
supportive source would move P-A only to 0.50, and the negative evidence already retrieved (the explicit null in
CIT-0009) argues against doing that without new direct evidence.

---

## A3.6 What this addendum does not authorise

1. It does not authorise any claim that the simulated system works, or that any recommendation is a real
   recipe.
2. It does not authorise starting Phase 3 work in this turn, Phase 2 ends here and the next phase begins only
   on your "continue".
3. It does not change any question, prior or falsifier in PREREG_V1: those remain as locked, together with the
   Phase 1 evidence that updated two of the priors.
