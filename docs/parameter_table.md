# Parameter table and sources

**Label:** INTERNAL · **Date:** 2026-10-07 · **Companion to:** `docs/literature_review.md`
**Rule applied:** every numerical range carries a value, a unit, a source, and a class
saying whether the source is **directly about food-waste anaerobic digestion** (`direct`), about a **related
system** (`analogous`), or is an **ASSUMPTION FOR SIMULATION** with an explicit sensitivity range. Nothing is
described as experimentally established unless a retrieved source says so.

**Source classes**

| Class | Meaning |
|---|---|
| `direct` | The source measured food waste (or food-waste-derived substrate) in an anaerobic-digestion context. |
| `analogous` | Related substrate or system (sludge, lignocellulose, co-digestion, different protocol or pre-treatment agent). |
| `assumption` | No source supports the value; it is a modelling choice. |

**Citation status** (identifier resolves **and** title/first-author/year match **and** the cited section
supports the sentence)

| Code | Meaning |
|---|---|
| `V-FULL` | Record opened this session; metadata matched; cited section read. **One record (CIT-0028) is `V-FULL` at abstract + introduction depth**: the results section was not read, and the +41 % figure quoted from it comes from its abstract. The ledger records this as `open_full_text_partial`. |
| `V-META` | Metadata verified via Crossref; cited content read from the publisher's indexed abstract/highlights, **not** full text. |
| `PARTIAL` | Content seen only through a search-index excerpt or a secondary table. |
| `UNVERIFIED` | Not retrieved. Can never support a number. |

---

## 1. Feedstock inputs

| # | Parameter | Simulated role | Range used | Unit | Class | Cite | Status | Applicability note | Sensitivity range |
|---|---|---|---|---|---|---|---|---|---|
| S1 | Carbohydrate fraction | Primary energy carrier | 0.45 – 0.74 (sampled triangularly, mode 0.65) | fraction of volatile solids | `direct` | CIT-0008 | `V-META` | The indexed excerpt reports ≈12–74 % across studies. **Band narrowed in Phase 2 from 0.30–0.70 to 0.45–0.74** because a uniform box over the old band is nearly infeasible under the simplex constraint (66 % of draws rejected, survivors forced lipid-rich); the new band stays inside the sourced spread. Recorded as decision S-6. **The band edges remain a modelling choice even though the phenomenon is sourced.** | 0.20 – 0.80 |
| S2 | Protein fraction | Energy carrier + ammonia precursor | 0.05 – 0.25 | fraction of volatile solids | `direct` | CIT-0008, CIT-0003 | `V-META` | Indexed excerpt reports ≈13.8–18.1 %; the broader literature spread is wider than the simulated band. | 0.03 – 0.30 |
| S3 | Lipid fraction | Highest methane potential; inhibition source above a threshold | 0.02 – 0.30 | fraction of volatile solids | `direct` + `analogous` | CIT-0008, CIT-0009 | `V-META` / `V-FULL` | Indexed excerpt reports 3.78–33.72 %; lipid-rich waste carries the highest reported methane potential of the food-waste fractions [CIT-0009, opened]. Indian hotel food waste is explicitly described as containing fat/oil/grease alongside resistant components [CIT-0028], supporting a **wide** lipid band rather than a narrow one. | 0.01 – 0.40 |
| S4 | Fractions sum to 1 | Structural constraint | enforced to 1 ± 1e-9 | – | `assumption` | – | – | Bookkeeping requirement of the simulator, not a literature claim. Reported values are inconsistent in *basis*, see §5 caveat 3. | – |
| S5 | Total solids (TS) | Wet/dry regime descriptor | 5 – 20 | % wet weight | `direct` | CIT-0006 (`V-FULL`), CIT-0012 (`V-META`) | `V-FULL` / `V-META` | CIT-0006 tested 5–20 % TS in food-waste AD and classified wet ≤10 %, semi-dry 10–20 %, dry ≥20 %. **Conflict:** CIT-0006 found better performance at higher TS up to 20 %; CIT-0012 found a specific methane-yield *reduction* at 20 % (259.8 vs 278.8–291.7 NmL/g VS at 5–15 %). Both are kept (claim C-005). | 3 – 25 |
| S6 | Moisture content | Reported cross-check only | 70 – 90 | % wet weight | `direct` | CIT-0003 | `V-META` | ≈70–74 % in the measured study; 74–90 % across the literature it cites. Ambient **relative humidity is not used anywhere**: see §6, R14. | – |
| S7 | VS/TS ratio | Cross-check on organic content | 0.80 – 0.97 | – | `direct` | CIT-0003 | `V-META` | Measured 83–87 %; literature 80–97 %. Used to sanity-check generated data, not as an input. | – |
| S8 | C/N ratio | Cross-check only | 14.7 – 36.4 | – | `direct` | CIT-0003 | `V-META` | Not a model input: derivable from S1–S3, so feeding it separately would double-count. | – |

## 2. Pre-treatment inputs (the hypothesis under test)

| # | Parameter | Simulated role | Range used | Unit | Class | Cite | Status | Applicability note | Sensitivity range |
|---|---|---|---|---|---|---|---|---|---|
| P1 | Pre-treatment duration | Fungal contact time | 0 – 96 | h | `analogous` | CIT-0018, CIT-0019, CIT-0028 | `PARTIAL` / `V-FULL` | Literature durations run from minutes (thermal, 10–20 min [CIT-0028]) through 7 days (alkaline + fungal step on park waste, +22.7 % biogas [CIT-0034]) to 30 days (fungal on wood [CIT-0018, CIT-0019]); fungal outcomes can *reverse* with longer cultivation [CIT-0032]. The 0–96 h window is a **scaling choice for a compact simulation**, not a literature optimum. | 0 – 7 days |
| P2 | Pre-treatment net effect factor | Availability gain **minus** degradable-mass loss | 0.70 – 1.60 (centred on 1.00 = no effect) | dimensionless multiplier | `assumption`, span anchored on `direct`+`analogous` evidence | CIT-0007, CIT-0005, CIT-0009, CIT-0018, CIT-0019, CIT-0028 | `V-META` / `V-FULL` / `PARTIAL` | **Benefit side:** an oriented consortium-based compound enzyme that **names *Aspergillus oryzae* as its protease generator** raised food-waste biomethane from 335.3 to 423.5–522.6 mL/g VS (+27 % to +56 %; best 522.61 mL/g VS) [CIT-0007]; thermal pre-treatment of Indian hotel food waste raised cumulative biogas 41 % over control [CIT-0028]; a fungus-grown-on-food-waste mash doubled the methane *rate* of sludge digestion and cut lag time 80 % [CIT-0005]. **Harm side:** fungal pre-treatment of willow sawdust decreased methane yield ≈34.7 % with one fungus while increasing it ≈43.1 % with another [CIT-0018, CIT-0019]; the Jaipur paper's introduction lists food/kitchen-waste pre-treatment outcomes from −7.5 % (methane) and −11.7 % (vegetable waste) upward, with higher severity the harmful direction [CIT-0028]; and an opened review states outright that fungal pre-treatment of agricultural biomass **did not improve** biomethane yield and is reported as less effective than other methods [CIT-0009], while a further review finds a **negative** impact of two fungi and a positive impact of two others on the same substrate [CIT-0032]. **No retrieved study applies pure *A. oryzae* to food waste and then digests that same food waste.** | 0.5 – 2.0 |
| P3 | Availability gain vs degradable-mass loss, modelled separately | Two terms so harm and benefit can both arise | gain 0.80 – 1.50 ×; loss 0.00 – 0.20 of VS | – | `assumption` | CIT-0016, CIT-0028 | `V-META` / `V-FULL` | Separated because the literature reports both improved hydrolysis and organic-matter loss during pre-treatment (2.6–9.9 % COD loss in aerobic pre-treatment [CIT-0016]); the split magnitudes are mine. | gain 0.7–1.8; loss 0–0.3 |
| P4 | Temperature during pre-treatment | Fungal growth condition | 25 – 35 | °C | `analogous` | CIT-0005 | `V-FULL` | The retrieved *A. oryzae* food-waste fermentation study used controlled incubation; the simulator treats pre-treatment as a bounded box with a net effect (P2), **not** as a growth model. Specific optima are therefore not extracted. | 20 – 40 |

## 3. Anaerobic-digestion process inputs

| # | Parameter | Simulated role | Range used | Unit | Class | Cite | Status | Applicability note | Sensitivity range |
|---|---|---|---|---|---|---|---|---|---|
| D1 | Digestion temperature | Activity modifier with two optima | 20 – 60 | °C | `direct` | CIT-0010, CIT-0011, CIT-0028 | `V-META` / `V-FULL` | Mesophilic optimum **31–35 °C**, thermophilic **50–60 °C**; 35 °C described as optimal overall [CIT-0010]. The Indian hotel-waste batch assay ran at **37 °C** [CIT-0028]. The two-plateau *shape* is my modelling choice. | 15 – 65 |
| D2 | pH | Activity modifier, sharp penalty outside a narrow band | optimum 6.8 – 7.2; modelled range 5.5 – 8.5 | – | `direct` | CIT-0010, CIT-0011 | `V-META` | 6.8–7.2 optimal, ≈6.5–8.5 acceptable; below ≈6.5 associated with acidification. | 6.0 – 8.0 |
| D3 | Organic loading rate (OLR) | Loading intensity with an overloading penalty | 0.5 – 6.0 | kg VS m⁻³ d⁻¹ | `direct` | CIT-0011 | `V-META` | Food waste was tested at 1–4 kg VS m⁻³ d⁻¹ with VFA-driven inhibition at higher loading (thermophilic mono-digestion). Continuous-process concept used as a flat descriptor, see §5 caveat 1. | 0.3 – 8.0 |
| D4 | Hydraulic retention time (HRT) | Digestion completeness term | 10 – 40 | days | `direct` | CIT-0010 | `V-META` | Ideal ≈10–25 days; mesophilic 20–30; thermophilic ≈15; washout risk below ≈10. | 5 – 60 |
| D5 | Inoculum-to-substrate ratio (I:S, VS basis) | Seed-availability term with diminishing returns | 0.5 – 4.0 | g VS inoculum per g VS substrate | `analogous` | CIT-0004; standard not retrieved: CIT-0017 | `V-FULL` | VDI 4630 recommends substrate-to-inoculum **below 0.5** (I:S > 2); the older convention was 1:1 [CIT-0004]. The standard itself (CIT-0017) is paywalled and was **not** retrieved, so this value is secondary-source only. Basis declared explicitly (decision S-3). | 0.25 – 6.0 |
| D6 | Lipid-inhibition threshold | Composition penalty for lipid-rich feed | onset ≈0.20–0.25; severe ≈0.5 | g LCFA / oleate per L reactor liquid | `analogous` | CIT-0015, CIT-0007 | `PARTIAL` / `V-META` | Onset reported above ≈250 mg/L (non-acclimated) and ≈400–450 mg/L (acclimated) [CIT-0015]; profound inhibition quoted at 0.2 g oleate/L and cessation at 0.5 g/L [CIT-0007 introduction]. **These are bulk-reactor concentrations, not substrate fractions**: the conversion is a modelling assumption (§5 caveat 2). | onset 0.1 – 0.5 g/L |
| D7 | Ammonia-inhibition threshold | Composition penalty for protein-rich feed | TAN 1.5 – 5.0 (severe above ≈5) | g TAN per L | `analogous` | CIT-0014, CIT-0011 | `V-META` | IC₅₀ measured at **19.0 g TAN/L** at 35 °C [CIT-0014], while 50 % inhibition is reported from 1.7 to 14 g/L across studies. The simulated penalty band is deliberately conservative and wide **because the spread is the finding**. | 1.0 – 8.0 g/L |
| D8 | Simulated digestion window | Window over which endpoint yield is defined (decision S-1) | 30 | days | `assumption` | CIT-0010 | `V-META` (for the band it sits in) | Chosen inside the reported 10–25 day ideal band and above the mesophilic 20–30 day range's floor, i.e. long enough to be an "endpoint" but not claiming full ultimate-potential completion. | 20 – 60 |

## 4. Outputs

| # | Parameter | Definition | Value/range | Unit | Class | Cite | Status | Note |
|---|---|---|---|---|---|---|---|---|
| O1 | `simulated_methane_yield` (primary target) | Simulated specific methane yield per unit volatile solids, over the D8 window | 0 – 600 (clamped) | **mL CH₄ g⁻¹ VS at STP** | unit convention `direct`; **values simulated** | CIT-0004 (unit), CIT-0003 (magnitude) | `V-FULL` / `V-META` | **Unit adoption (decision D4, see addendum 02).** The unit convention comes from an opened, open-access BMP methods source that defines normalised gas volume per gram VS at STP and states 1 g COD = 0.35 L CH₄ (STP) [CIT-0004]. Magnitude anchor: measured food-waste yields of **348 mL/g VS at 10 days and 435 mL/g VS at 28 days**, 73 % CH₄, 81 % VS destruction [CIT-0003]. **Every value the simulator produces is synthetic; it is not a BMP measurement and no BMP protocol is implemented.** |
| O2 | `simulated_biogas_yield` (secondary) | Modelled total gas per unit VS | derived | mL g⁻¹ VS | `assumption` | – | – | Generated consistently from O1 and O3 so the three outputs cannot contradict each other. |
| O3 | `simulated_methane_fraction` (secondary) | CH₄ share of the modelled biogas | 0.50 – 0.75 | v/v | `direct` | CIT-0003, CIT-0009 | `V-META` / `V-FULL` | 73 % measured in one food-waste study [CIT-0003]; reviews describe biogas as typically 50–75 % methane [CIT-0009]. |
| O4 | `simulated_stability_indicator` (secondary / optimiser constraint) | VFA-accumulation proxy for the feasibility test | 0 – 1 (0 = stable) | dimensionless | `assumption`, constrained by `direct` evidence | CIT-0010, CIT-0012 | `V-META` | An internal construct, **never** a measurement. It exists so the optimiser cannot recommend settings that the simulator itself marks unstable. Threshold anchored on the reported VFA–biogas relationship [CIT-0010] and on observed TVFA maxima at high solids [CIT-0012]. |

## 5. Scale and scope caveats (must travel with this table)

1. **Batch vs continuous.** The simulation generates "batches" with replicate noise, but OLR, HRT and I:S are
   continuous-process or batch-assay descriptors. The simulator treats them as *flat* descriptors of a
   digestion setting; it models no hydraulic dynamics, washout kinetics or reactor geometry. The model notes state
   this in the spec, and the report must not present simulated HRT/OLR effects as reactor-design advice.
2. **Concentration vs composition.** Lipid and ammonia inhibition are reported as bulk concentrations
   (g LCFA/L, g TAN/L), whereas the simulator's inputs are substrate fractions plus TS. Converting fractions
   into concentrations requires an assumed loading and liquid volume: a modelling step, labelled `assumption`,
   with its sensitivity explored by the sensitivity sweep.
3. **Basis inconsistency.** Reviews report carbohydrate/protein/lipid "percentages" on inconsistent bases
   (wet weight, % TS, % VS). The simulator declares **one** basis, fraction of volatile (organic) solids, and
   this table records that decision rather than inheriting the confusion.
4. **Contaminant-blind.** Real hotel/household food waste contains egg shells, coffee grounds, tissue paper
   and bone that behave differently in digestion [CIT-0028]. The simulator has no term for them; this is an
   explicit simplification for report §9.
5. **Not a recipe.** Nothing in this table transfers to a real digester: the ranges bound a *simulated*
   response surface, and several are assumptions by construction.

## 6. Output-contract compliance checks

| Rule | Check | Result |
|---|---|---|
| R13: every range has value/unit/source-or-assumption | Every row in §1–§4 carries a class and a cite, or an explicit `assumption` label | PASS |
| R14: ambient relative humidity excluded unless justified | No row uses relative humidity; moisture appears only as a reported cross-check (S6). No retrieved source supports ambient RH as a driver of slurry methane potential | PASS (excluded, reason recorded) |
| **Physical unit rule**: used only because a verified source specifies a standard unit and conditions this simulation can mirror | **Condition met** by CIT-0004 (`V-FULL`, open access, opened this session; metadata re-confirmed via Crossref): it defines normalised gas volume per gram VS at STP and the COD conversion. Guard rails now mandatory: (a) internal quantity stays scale-free; the unit is a declared **scale-adoption**; (b) `SIMULATED` on every artifact; (c) the report must state that **no BMP protocol is implemented**; (d) the unit convention is cited separately from simulated effect sizes | **Adopt physical unit, with guard rails** |
| **Physical units** | The yield column carries the scale-adoption note | Enforced by a schema test |
| No invented values | Every number traces to a row in `docs/references.md`; nothing written from memory | PASS |
| Unverified sources excluded from the table | CIT-0017 (VDI 4630, paywalled, not retrieved) appears only as a *gap note*; the I:S value it would support is cited from a secondary source [CIT-0004] | PASS |
| Negative/absent evidence recorded | The "no *A. oryzae* on food waste → same food waste" search outcome is written down rather than filled in | PASS: `docs/literature_review.md` §2.4 |

## 7. What the modelling step has to decide with these inputs

1. Which rows become **model inputs** versus **reported context** (S6–S8 are context-only candidates).
2. The fraction → concentration conversion for D6/D7 (§5 caveat 2), stated as an assumption with sensitivity.
3. Functional forms (unimodal for D1/D2; interaction for D3 × D4), each labelled `assumption` with its
   sensitivity range carried into the sweep.
4. **How P2 enters:** as a multiplier on the endpoint ceiling only, on the rate only, or on both. The evidence
   points to rate more often than to ultimate potential [CIT-0016], while the Jaipur result is a 45-day
   cumulative change [CIT-0028], the model has to choose, and the report states which choice was made.
