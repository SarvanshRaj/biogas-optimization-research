# Known issue: five sanity anchors do not reproduce from the equations

Companion to `docs/model_specification.md`. It records what the equations actually produce, where the
section 4.1 sanity values were written down wrong, and which implementation decisions were needed to build a
working generator. No equation, constant, research question or decision rule changes because of it.

**When:** at the point `src/simulate_data.py` first ran, before any dataset was written, before any model was
fitted. No result can be affected by these decisions.
**Checked by:** `tests/test_spec_anchors.py` (15 tests).

---

## 1. Why check these at all

Section 4.1 of the model notes states that its own numbers came from "hand-arithmetic checks ... run in a
scratch session (**not** project code)". Arithmetic done that way drifts, so the first thing checked once the
simulator ran was every anchor, re-derived from the equations in sections 3.2 and 3.3 rather than trusted from
the table. The same rule as everywhere else in this study: a number that cannot be reproduced gets reported,
not inherited.

Reproduction command (deterministic, no randomness):

```bash
python3 -m pytest tests/test_spec_anchors.py -q
```

## 2. The comparison, anchor by anchor

`literal` = the implementation of sections 3.2/3.3 taken literally (inhibitors in **both** the
rate constant and the yield multipliers, exactly as the equation block prints them).
`variant-B` = the reading of the section 3.3 structural rule 1 ("the two inhibitors ... enter
**only** as direct multipliers on the yield"), that is, the same equations with `f_LCFA` and `f_TAN`
removed from `k`. Units: mL CH₄ g⁻¹ VS.

| Section 4.1 anchor | notes | literal | variant-B | literal − notes |
|---|---:|---:|---:|---:|
| Reference favourable | 412 | 411.6 | 412.6 | −0.4 |
| Typical mixed food waste | 399 | 399.2 | 401.3 | +0.2 |
| Low-lipid, high-carbohydrate | 370 | 369.6 | 370.0 | −0.4 |
| Lipid/protein-rich, mid operations | 349 | **274.7** | **312.0** | **−74.3** |
| High lipid **and** high TS/OLR | 217 | **191.7** | **206.2** | **−25.3** |
| Cold and acidic | 161 | **109.1** | **117.2** | **−51.9** |
| Pre-treatment, harmful (R 0.75) | 275 | 283.8 | 285.2 | +8.8 |
| Pre-treatment, neutral (R 1.00) | 362 | 373.3 | 374.3 | +11.3 |
| Pre-treatment, beneficial (R 1.30) | 466 | 479.6 | 480.1 | +13.6 |
| Pre-treatment at 24 h only | 437 | 450.0 | 450.7 | +13.0 |
| Held-out OOD, mild (l 0.35, TS 24, 55 °C) | 131 | **124.8** | **143.7** | **−6.2** |
| Held-out OOD, near edge (l 0.32, TS 22) | 201 | **187.1** | 202.7 | **−13.9** |
| Mid-range operations across the composition distribution | p05 388 / med 434 / p95 490 | p05 **387** / med **433** / p95 **488** || −1 / −1 / −2 |

## 3. What reproduces, and what does not

**Reproduces (within 1 mL/g VS):** the three central configurations, and, importantly, the
distribution anchor, which is the only one that exercises the composition sampler (realised p05 /
median / p95 within 2 mL/g VS of the written values, acceptance rate 64 % as designed).

**Does not reproduce, and why, three separate causes:**

1. **The loading-driven acidification channel (five anchors, −6 to −74).** Every configuration
   that diverges substantially has a non-trivial `VFA_stress`, i.e. it is affected by
   `pH_eff = pH_s − 0.8·VFA_stress` (section 3.2), which then enters `f_pH(pH_eff)` in the rate
   constant (section 3.3). The scratch session's values are consistent with evaluating `f_pH` at
   the *setpoint* rather than at the acidified value. The equation names `pH_eff`
   explicitly, so the implementation follows the equation, not the scratch table. Note that the
   anchor labelled "lipid/protein-rich, mid operations" gives stress ≈ 0.98, the model is doing
   what the specification says, and the summary number in the notes was computed on a
   milder path.
2. **An internal contradiction in section 3.3 (bounds the first cause).** Structural rule 1 says
   the inhibitors enter "only as direct multipliers on the yield", but the printed rate constant
   contains `× f_LCFA × f_TAN`. Under the literal (conservative) reading each inhibitor acts twice.
   Variant-B implements the rule-1 reading; the two readings differ by at most 37 mL/g VS across
   the anchor set (asserted in `test_inhibitor_channel_ambiguity_is_bounded`). **Decision:** the
   equation block is the operational definition and is implemented literally; the ambiguity is
   recorded here and quantified, and the sensitivity sweep covers it (`c_lcfa_half`, `c_tan_half`, `η`). It is
   not resolved by choosing whichever number looks better.
3. **A small uniform offset in the pre-treatment family (+2.9 % to +3.2 %, +9 to +14 mL/g VS).**
   The offset is the same for harmful, neutral and beneficial branches, so it cannot come from the
   availability channel (`avail` differs between branches). At 96 h, `g(96 h) = 0.9304`, so the
   scratch values would correspond to a slightly different `g(t)` or loss convention. This drift
   is unexplained and is recorded as unexplained; it is small relative to the effect being
   demonstrated (the harmful-to-beneficial span is 284 → 480, i.e. ±26 % around neutral, versus
   the claim written in the notes of "275 → 466, ±~26 %", the *span* claim survives, the endpoints move).

**What does not survive:** the sentence in the notes that "the central configurations land inside the measured
food-waste band (348–435 mL/g VS)". Three of them do (412 / 399 / 370). The lipid/protein-rich mid-operations
configuration does not: it lands at 275 under these equations. The results report that, rather than describing
all the anchors as inside the band.

## 4. The held-out family: a conflict in the notes that needed a decision

Section 8 of the model notes requires the held-out family to extend lipid fraction (0.30–0.38) and total
solids (22–28 %), with "other variables inside their normal ranges". Implemented literally, every
other axis sampled across its full training range, the family collapses:

| Sampling of the non-extended axes | mean | min | exact zeros | verdict |
|---|---:|---:|---:|---|
| Independent draws across the full training range | 28.1 | 0.0 | yes | section 4.1 (iii) violated: metrics on a family that contains exact zeros are uninformative, and a failure could not be blamed on the extended axes |
| **Central bands** (`config.OOD_CENTRAL_BANDS`), adopted | 41.5 | 0.1 | no | low, non-degenerate, and the degradation is attributable to the two extended axes |

Both variants are recorded because the choice is a design decision, not an arithmetic fact. The
adopted version keeps the two extended axes at 0.30–0.38 lipid and 22.03–27.92 % total solids
(verified in `test_ood_lies_outside_the_training_support_on_two_axes`) and reproduces the two OOD anchor
configurations in the notes to within 7 and 14 mL/g VS (124.8 vs 131; 187.1 vs 201).

The central bands are: temperature 30–55 °C, pH setpoint 6.5–7.5, OLR 1.5–4.0, HRT 20–35 d,
inoculum ratio 1.0–3.0, pre-treatment 0–96 h and 25–35 °C. They are inside the training ranges, so
section 8 is satisfied; they exclude the corners that made the probe uninterpretable.

## 5. Decisions taken while building the generator (all before any result existed)

| # | Decision | Reason | Evidence |
|---|---|---|---|
| A3-C1 | Implement the equation block literally (inhibitors in both channels) | the equation block is the definition; the conservative direction is noted | `tests/test_spec_anchors.py` |
| A3-C2 | Held-out family uses central bands for the non-extended axes | section 4.1 (iii), so an extrapolation failure can be attributed | `tests/test_ood_split_validation.py` |
| A3-C3 | No inoculum term in the yield equation | section 3.3 contains none, and section 13.1 calls I:S a flat descriptor; the reference and typical anchors reproduce exactly **only** without it | `test_inoculum_ratio_is_a_flat_descriptor` |
| A3-C4 | Round only the four columns section 3.6 lists | rounding extra columns was not asked for and would change the data | `config.ROUNDING` + validator tests |
| A3-C5 | Validate the held-out family against `OOD_RANGES`, not the training envelope | its whole purpose is to sit outside the training envelope | `test_ood_frames_validate_against_the_ood_envelope` |
| A3-C6 | Derived correlations above the 0.20 design threshold must be declared | `ph_measured` is computed from loading, so it is legitimately correlated with OLR (r = −0.349); an undeclared one would be a silent design defect | `test_derived_correlations_are_documented_not_silent` |

## 6. What to do with this

- To check the claims: run `pytest tests/test_spec_anchors.py -q`. Every number in §2 and §4 is
  pinned; if a future change moves one, the test fails.
- To correct the table itself: the anchor table in `docs/model_specification.md` §4.1 is left as written, and
  this note is the correction. If it is ever edited, the change goes at the bottom of that file with the reason.
- The strongest objection available is to A3-C2: someone could argue the held-out family should keep the literal
  full-range sampling and simply report the degeneracy. The counter-argument is in the table above, and the
  literal variant's statistics are kept so that the objection can be checked without re-running anything.
