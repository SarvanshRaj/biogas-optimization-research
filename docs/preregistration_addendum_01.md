# PREREGISTRATION ADDENDUM 01, resolution of the four blocking questions

**Applies to:** `docs/preregistration.md` (PREREG_V1)
**Original lock (unchanged):** SHA-256 `8d3666e8b6532f0281d31e85f6dcde9e2f7dcd08b72d4173dc985b47361b966f`
**Recorded:** 2026-10-07T06:24:16+00:00
**Timing, stated because it matters:** these answers were given by the user **at the close of Phase 0 and
before Phase 1 opened**. No evidence had been gathered and no code existed when the decisions were made, so
these are **pre-evidence resolutions of questions the preregistration itself listed as open**: not post-hoc
adjustments. Nothing here is labelled AD_HOC. The original preregistration file is left byte-identical so its
lock hash still verifies; this addendum carries the resolutions, and is itself hashed below.

---

## A1 · D4, Target scale: **conditional on Phase 1 evidence**

| | |
|---|---|
| User's answer | Attach a physically-labelled simulated yield **if Phase 1 justifies it** |
| Resolution rule (fixed now, before the evidence) | **Adopt a physical unit only if** a retrieved, verified source specifies a standard methane-potential unit *and* the conditions its protocol defines are ones this simulation can plausibly mirror. Then the target becomes e.g. `mL CH4 g⁻¹ VS`, always printed as `simulated_mL_CH4_per_g_VS`. **Otherwise** the target stays the dimensionless `simulated_yield_index` in [0, 100]. |
| Mandatory guard rails either way | (1) The internal quantity stays scale-free; a physical label is a *scale-adoption* for interpretation, and the report must say so in those terms. (2) Every artifact states the data are synthetic. (3) No artifact presents a yield as measured or as a prediction for real food waste. (4) The adopted source is cited in the parameter table with `source_class = direct` for the *unit convention* (never for the simulated effect sizes). |
| Decided by | Phase 1 finding RH-09 (protocol/units) · recorded in `docs/sources.json` |
| If the rule fires to "no" | Dimensionless index; report states that no retrieved source justified a physical scale for this simulation. |

## A2 · D5, Dataset size and seeds: **locked**

500 scenarios × 8 replicates = **4,000 rows**, **5 seeds** over the whole generate → split → fit → score path.
Reason recorded at lock and repeated here: a runtime and coverage trade-off on a 2 vCPU / no-GPU sandbox.
**It is explicitly not a statistical-power argument**, and no artifact may describe it as one.

## A3 · D3, License: **confirmed**

`LICENSE` (MIT) for code and `LICENSE-docs` (CC BY 4.0) for documentation and the report, plus a short
licensing note in the README, added together with the code, as
planned in the decisions register.

## A4 · Audience, **public repository**

The repo is public, so the README and report are written for a **public portfolio audience**: the student's
name only, no other personal identifiers, no school or programme details beyond what the student states
himself, and no contact information. Confidentiality of the *run* stays **INTERNAL** (working state), while
the *deliverables* are written to be publishable as-is.

## A5 · Defaults accepted silently (both reversible, neither blocks Phase 1)

- **Figure style:** plain matplotlib, colour-blind-safe palette, no decorative graphics. If the school needs
  a specific submission format, say so and it will be adjusted in Phase 4.
- **Language:** English throughout; the student-explanation section of the report can be duplicated in Hindi
  on request.

---

## Effect on the locked test set

Unchanged. `docs/test_matrix.md` already contains the tests these decisions feed (D-CFG-* for the unit field
and provenance, D-SCH-04 for labelling, D-REPO-02 for pins, D-DOC-02 for disclaimers). If Phase 1 fires A1
to "physical unit", one extra test is added, `D-SCH-06`: every artifact carrying a physical unit must also
carry the scale-adoption note and the SIMULATED marker.

**Addendum SHA-256:** `226eda3d28353617e895aa1bcb359f41cbed17a6046c58f3313ef615c683de9c`
