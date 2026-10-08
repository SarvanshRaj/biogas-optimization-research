# Pre-registration addendum 02, post-evidence decisions

**Label:** INTERNAL · **Date:** 2026-10-07 · **Status:** active amendment, recorded **after** the Phase 1
evidence pass and **before** any Phase 2 modelling decision.
**Relationship to the lock:** `docs/preregistration.md` (PREREG_V1, SHA-256
`8d3666e8b6532f0281d31e85f6dcde9e2f7dcd08b72d4173dc985b47361b966f`) is **not edited**. This addendum records
decisions that the evidence pass made answerable; it cannot change a hypothesis or a falsifier, only how they
are implemented.

---

## A2.1, Decision D4 is resolved: the physical unit is ADOPTED, with guard rails

**The conditional you set was:** a physical unit may be used *only if* Phase 1 retrieves a verified source
that justifies the scale (for example, a BMP protocol defining conditions the simulation can mirror).
Otherwise the dimensionless index stays.

**Outcome: the condition is MET, and the unit is adopted.**

- **Source:** CIT-0004, Filer, Ding & Chang (2019), *Biochemical Methane Potential (BMP) Assay Method for
  Anaerobic Digestion Research*, **Water 11(5):921**, DOI `10.3390/w11050921`. Record opened in full this
  session; metadata re-confirmed against Crossref (title, first author, year, journal, volume, article
  number, CC-BY licence). Open access.
- **What it specifies that matters here:** the BMP result is reported as a normalised gas volume of methane
  per gram of volatile solids at standard temperature and pressure; the paper also states the convention
  that **1 g COD = 0.35 L CH₄ at STP** (0.395 L at 35 °C), reports a cellulose positive-control value of
  **415 mL CH₄/g VS (STP)**, and describes the German guideline (VDI 4630) practice of loading ~10 g VS/L
  and keeping the substrate-to-inoculum ratio below 0.5.
- **What the simulation may therefore claim:** the *unit convention* for the primary target
  **mL CH₄ g⁻¹ VS at STP**: because a retrieved, open, primary methods source publishes in exactly that unit
  and defines it.
- **What it may not claim (guard rails, all four mandatory):**
  1. **Scale adoption, not simulation of the protocol.** `simulated_methane_yield` adopts the *unit*. The
     simulator does **not** implement a BMP assay: no inoculum pre-incubation, no 10 g VS/L loading rule, no
     30-day incubation window, no 0.5 substrate-to-inoculum constraint, no positive control.
  2. **The unit convention is cited separately from simulated effect sizes.** CIT-0004 may be cited for the
     unit and for protocol context. It may **never** be cited as the source of a simulated percentage change.
  3. **`SIMULATED` on every artifact** that carries the unit (CSV header, figure label, metrics file, report
     table).
  4. **The report states the unit-adoption decision explicitly**, in the parameter table and in report §3,
     including the sentence that the simulation's values are synthetic and are not BMP measurements.
- **The dimensionless `simulated_yield_index` remains available** as an internal representation: the
  simulator computes a scale-free quantity first, then applies the unit as a declared conversion in one
  place (`src/config.py`, Phase 3). This keeps the choice reversible by a single constant.

**New test, now mandatory (D-SCH-06, conditional gate fires "yes"):**

> **D-SCH-06, physical-unit guard.** Given any generated artifact declaring a methane yield in
> mL CH₄ g⁻¹ VS: assert (a) the `SIMULATED` marker is present; (b) the scale-adoption note naming CIT-0004 is
> present; (c) an explicit no-BMP-protocol statement is present. **RED first** in Phase 3 (no implementation
> exists yet), recorded in `docs/notebook/test_log.md`, then GREEN.

---

## A2.2, Decision S-1: the target is an endpoint yield, and the rate/extent split is explicit

The evidence pass found that pre-treatment is reported to change the **rate** of methane production more
often than the **ultimate potential**: a 5-day aerobic pre-treatment left the methane potential essentially
unchanged (~418 mL/g VS, no significant difference) while raising the production rate by ≈22 % [CIT-0016,
`docs/literature_review.md` §2.3]. If the simulator had modelled "ultimate potential" only, that distinction
would have been assumed away without anyone noticing.

**Decision (S-1, renamed from D8 in Addendum 03 §A3.1):** the primary target `simulated_methane_yield` is an **endpoint yield over a fixed simulated
digestion window** (declared in Phase 2, default 30 simulated days, which is above the mesophilic HRT floor
and inside the 10–25 day ideal band reported in CIT-0010). The pre-treatment term is split into:

- `availability_gain`, how much more of the organic matter becomes accessible (deterministically affects the
  ceiling of the endpoint), and
- `degradable_mass_loss`, organic matter consumed or lost by the fungus itself (deterministically lowers the
  ceiling),

with the net factor `availability_gain − degradable_mass_loss` free to be **below 1.0** (harmful), **equal to
1.0** (neutral) or **above 1.0** (beneficial). This implements already-frozen process decision P6 and makes
the rate-versus-extent question visible in the output rather than hidden in the assumption.

**What this does not decide (Phase 2 must, and must say so):** whether the *rate* portion is also surfaced as
a separate secondary output. Recommendation carried forward: yes, as a secondary simulated output only, with
no claim that it reproduces any real kinetics.

---

## A2.3, Decision S-3: the inoculum convention is declared, not inherited

Two conventions coexist in the retrieved sources: VDI 4630 recommends a **substrate-to-inoculum ratio below
0.5** (i.e. I:S above 2), while the older baseline convention used **1 g VS substrate per g VS inoculum**
(I:S = 1) [CIT-0004]. The simulator's `inoculum_ratio` variable therefore **declares its basis** in the
parameter table as "g VS inoculum per g VS substrate" and is simulated over **0.5–4.0** with a sensitivity
range of 0.25–6.0. No retrieved source is claimed to fix its optimum for food waste; the term's shape is an
ASSUMPTION FOR SIMULATION.

---

## A2.4, Contradiction carried, not resolved (S-4)

Total solids: 5–20 % TS in mesophilic food-waste AD gave *better* performance at higher TS [CIT-0006,
record opened], whereas 5–20 % TS in co-digestion gave a statistically indistinguishable specific methane
yield across 5–15 % and a *reduction* at 20 % [CIT-0012, metadata verified]. Under Law 8 (no premature
synthesis) this is **not** averaged away. Both claims enter the claim graph (C-005), both are attributed, and
the simulator's TS response stays deliberately mild, and the sensitivity sweep covers it.

---

## A2.5, Process correction found during this pass (recorded as a failure, not hidden)

During the first search sweep of this phase, several **leads** were captured as content without their exact
locators being recorded (e.g. a journal article summary in a search-result snippet). Writing a citation from
such a lead would have produced exactly the failure the project forbids: a citation that looks precise and
cannot be checked. The affected items were therefore **removed from the documents and are listed as
uncited leads** in `docs/sources.json` → `leads_not_cited`, with the reason recorded.

Corrective rule adopted for the rest of the project: **a source's locator is captured in the same action that
captures its content.** Where a locator could be recovered in a bounded follow-up (three of them were:
CIT-0018–CIT-0023), the item was re-entered with a real locator and is cited with an honest access level;
where it could not, the item stays uncited.

---

## A2.6, What this addendum does *not* authorise

1. It does not authorise describing the pre-treatment stage as effective. No retrieved study tests *A. oryzae*
   on food waste followed by digestion of that same food waste (`docs/literature_review.md` §2.4).
2. It does not authorise any physical claim about a real digester. The unit is a reporting convention for a
   synthetic quantity.
3. It does not close Phase 1 by itself: the evidence documents and the source records are the
   Phase 1 deliverables; this addendum records the decisions they forced.
