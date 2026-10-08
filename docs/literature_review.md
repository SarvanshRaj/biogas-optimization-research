# Literature review: what the evidence says

**Label:** INTERNAL · **Date:** 2026-10-07 · **Scope:** what the retrieved evidence supports, what it
contradicts, and what remains unknown. Companion to `docs/parameter_table.md` (the numeric provenance).
**Status codes:** `V-FULL` (record opened; metadata matched; cited section read) · `V-META` (metadata verified
via Crossref, title, first author, year match; cited content read from the publisher's indexed
abstract/highlights, **not** the full text) · `PARTIAL` (content seen only through a search-index excerpt,
secondary table, or citation in another paper) · `UNVERIFIED` (not retrieved; cannot support a number).

**Reading rule:** nothing here is a claim about a real digester built by this project. It is background for a
simulation whose outputs are synthetic. Where a source is `PARTIAL`, the sentence says so.

---

## 1. The two stages, in plain terms

**Stage 1, fungal pre-treatment.** Some fungi secrete enzymes that break large molecules in organic waste
into smaller, more accessible ones. The project's hypothesis is that *Aspergillus oryzae* might do this for
food waste, making more of it available to the microbes in stage 2. The hypothesis is testable only in a
laboratory; in this project it is a **parameter**, never a conclusion.

**Stage 2, anaerobic digestion (AD).** Without oxygen, a microbial community converts organic matter through
hydrolysis → acidogenesis → acetogenesis → methanogenesis into biogas (mainly methane and carbon dioxide)
plus a nutrient-rich residue. A retrieved review describes exactly this four-step chain and lists the
governing operational factors: feedstock characteristics, total solids, retention time, pH, C/N ratio,
temperature, organic loading rate, volatile fatty acids and seeding [CIT-0009, `V-FULL`].

**Why food waste is a favourable substrate.** Measured food waste showed ~70–74 % moisture, a VS/TS ratio of
83–87 %, **348 mL CH₄/g VS after 10 days and 435 mL CH₄/g VS after 28 days**, an average biogas methane
content of 73 %, and 81 % VS destruction at 28 days, which the authors describe as indicating high
biodegradability [CIT-0003, `V-META`].

**Why "highly degradable" cuts both ways.** Because food waste already degrades well on its own, the headroom
for a pre-treatment gain is structurally smaller than for wood or straw, and the retrieved pretreatment
literature is dominated by exactly those lignocellulosic substrates [§2.2].

---

## 2. The pre-treatment question: what the evidence actually shows

Highest-priority rabbit holes (RH-01, RH-02, RH-04). The honest summary is **mixed, mostly indirect, and it
does not support writing "pre-treatment improves methane yield" into the simulator.**

### 2.1 Evidence found, ordered by how directly it matches the hypothesis

| Evidence | What it actually did | Status | Match to the hypothesis |
|---|---|---|---|
| *A. oryzae* grown **on food waste** to produce a hydrolase-rich fermentate, then added to **sewage sludge** digestion: methane rose from **2140 mL to 7187 mL**; **24.3 %** of the gain attributed to the enriched hydrolase, 46.0 % to the added food-waste organics; sludge hydrolysis improved >50 % with 15 g fermented food waste per 200 g sludge; BOD₅/COD of the pretreated sludge rose 0.33 → 0.41 [CIT-0005] | Fungus × food waste, yes, but the digested substrate is **sludge** | `V-FULL` + Crossref | **Indirect.** Wrong substrate at the digestion step, and part of the gain is simply added substrate. |
| An *Aspergillus*-based oriented microbial consortium produced in situ, applied to **food waste itself**: biomethane yield rose from **335.3 → 423.5–522.6 mL/g VS**, i.e. **+27 % to +56 %**, with the highest yield (522.61 mL/g VS) at 1:100 dosing. The consortium **names *Aspergillus oryzae* as the protease generator** and *Aspergillus niger* as the amylase generator [CIT-0007] | Food waste pretreated, food waste digested | `V-META` | **Closest retrieved match**, and the reason prior P-A moves. Still not *A. oryzae* alone, the enzyme ratio is tuned and the preparation is a consortium, and it is a single study. |
| Indian hotel food waste (Jaipur), 45-day batch test at 37 °C: thermal pre-treatment at **100 °C for 10 min** raised total cumulative biogas production by **41 % over the control**; the effect is attributed to improved degradation of protein and volatile solids [CIT-0028] | Food waste, pre-treated, digested, but **thermal**, not fungal | `V-FULL` (abstract + introduction read) | **Analogous.** Same substrate and same *stage-1-then-stage-2* logic, different pre-treatment agent. Useful as a magnitude anchor for a *signed* pre-treatment factor. |
| A review of AD pre-treatments records that *Aspergillus*, *Sporotrichum*, *Penicillium* and *Fusarium* were used to pre-treat **orange processing waste** and increased biogas production [CIT-0009 citing Srilatha et al. 1995] | Fruit-processing waste, not mixed food waste | `V-FULL` (review) / `UNVERIFIED` (primary) | **Analogous.** The primary source was not retrieved; the claim is quoted from the review and is labelled as such. |

### 2.2 Evidence pointing the other way

- **Pre-treatment can reduce methane yield.** On the same substrate (willow sawdust) at the same cultivation
  duration (30 days), one white-rot fungus (*Leiotrametes menziesii*) **decreased** methane yield by ≈**34.7 %**
  while another (*Abortiporus biennis*) **increased** it by ≈**43.1 %**: from a review's own comparison table
  [CIT-0018, `PARTIAL`]; the Abortiporus study's own abstract likewise reports a **reduction** in methane yield
  for nitrogen-supplemented samples relative to the control [CIT-0019, `PARTIAL`], and a second review tabulates
  the same pair of outcomes [CIT-0020, `PARTIAL`]. **Strain and condition, not "fungal pre-treatment", decide
  the sign of the effect.**
- **The negative direction is stated explicitly in an opened source.** The retrieved review records that fungal
  pre-treatment of agricultural biomass **did not improve** biomethane yield (Paul et al. 2018, cited therein) and
  that fungal pre-treatment is reported as **less effective** than competing techniques (Kamusoko et al. 2019,
  cited therein) [CIT-0009, `V-FULL`]. A second review reports corn-silage biogas enhanced by two fungi but a
  **negative** impact from two others on the same substrate [CIT-0032, `PARTIAL`].
- **The same is true for pre-treatment generally, including the Indian case.** The Jaipur study's own
  introduction lists kitchen-waste or food-waste pre-treatment outcomes across the literature ranging from
  **+41 % and +40 % and +24 %** on one side to **−7.9 % (kitchen waste), −11.7 % (vegetable waste) and −7.5 %
  (methane)** on the other, depending on temperature, duration and substrate [CIT-0028, `V-FULL`]. Higher
  severity is repeatedly the harmful direction; the harmful cases are attributed to side products such as
  melanoidins [CIT-0028, `V-FULL`].
- **Fungal pre-treatment is overwhelmingly studied on lignocellulosic substrates**: wood, straw, crop
  residues, where the mechanism is delignification and cell-wall breakdown [CIT-0009 `V-FULL`; CIT-0018 and
  CIT-0020 `PARTIAL`]. Food waste contains little lignin. The mechanism that makes fungal pre-treatment
  attractive elsewhere may not transfer, which is the single most important finding of this phase for the
  project's own design.

### 2.3 Rate versus extent: a distinction the simulator must respect

The most consequential methodological finding: **pre-treatment often changes how fast methane is produced
rather than how much is ultimately produced.**

- Aerobic pre-treatment of food waste (2, 5, 8 days) produced **no significant difference in methane yield
  potential (~418 mL/g VS, p > 0.05)**, while a suitable 5-day duration raised the methane production *rate*
  by ≈**22 %**, at the cost of **2.6–9.9 % COD loss** during the aerobic stage [CIT-0016, `V-META`].
- Conversely, the Jaipur study measured a **41 % increase in cumulative biogas over 45 days** [CIT-0028],
  which at that window is closer to a change in extent than in rate, a reminder that "rate versus extent"
  also depends on **how long you measure**.
- The same pattern appears in BMP *methods* research: pre-incubated and non-incubated inocula gave **no
  significant difference in methane yield** (≈114 mL CH₄/g TCOD) while maximum production **rates** differed,
  and the seed source was found to underestimate ultimate biodegradability [CIT-0031, `PARTIAL`].

**Consequence for this project:** the primary target is
an **endpoint yield over a fixed simulated window**, and the pre-treatment term is split into
`availability_gain` and `degradable_mass_loss` so that harmful, neutral and beneficial outcomes are all
reachable. Whether the rate portion is surfaced separately is a modelling decision, argued explicitly below.

### 2.4 What was *not* found

No retrieved study tests **pure *A. oryzae* applied to food waste, followed by anaerobic digestion of that
same food waste**. Searches included the hypothesis as stated, synonym and spelling variants, explicit
contrary/failure phrasings, and a catch-all for the organism-and-substrate pair. The absence is evidence of its
own kind:
the project's two-stage concept, exactly as stated, is **not directly supported by a retrieved source**, so
the simulator must treat the pre-treatment effect as a wide, symmetric, explicitly-assumed factor. That the negative direction is *published*, not merely absent, is
recorded above (§2.2); the failure-query pass is what surfaced it.

**Effect on falsifier F1:** part-fires in the favourable direction. Adjacent evidence exists (food-waste enzyme pre-treatment, +27–56 %
[CIT-0007]; fungus-grown-on-food-waste to treat sludge [CIT-0005]; thermal pre-treatment of Indian hotel food
waste, +41 % [CIT-0028]), and the closest match **names *A. oryzae* explicitly** as the protease generator in a
two-fungus consortium (+55.87 % [CIT-0007]); a further source shows the **reverse** coupling, *A. oryzae* grown
on the VFAs produced *by* food-waste digestion [CIT-0033], so the organism and the two stages appear in the
literature in both orders, though not in this project's order. The exact concept is therefore still unsupported.
Therefore the pre-treatment factor **keeps its
symmetric assumed range (0.70–1.60×, centred on no effect)**, the simulator never hard-codes an improvement,
and prior P-A moves moderately (0.30 → 0.40) rather than decisively.

---

## 3. Process parameters: what governs stage 2

| Factor | Evidence | Status |
|---|---|---|
| Temperature | Mesophilic optimum **31–35 °C**; thermophilic **50–60 °C**; 35 °C described as optimal overall [CIT-0010]; thermophilic food-waste work operated at 50–60 °C [CIT-0011]; the Indian hotel-waste batch test used **37 °C** [CIT-0028] | `V-META` / `V-FULL` |
| pH | Optimal **6.8–7.2**; acceptable band ≈6.5–8.5; below ≈6.5 associated with acidification [CIT-0010]; 6.5–7.5 quoted in food-waste thermophilic work [CIT-0011] | `V-META` |
| OLR | Food waste tested at **1–4 kg VS m⁻³ d⁻¹**, with VFA-driven inhibition at higher loading, especially thermophilic mono-digestion [CIT-0011] | `V-META` |
| HRT | Ideal ≈**10–25 days**; mesophilic 20–30 days; thermophilic ≈15 days; washout risk below ≈10 days [CIT-0010] | `V-META` |
| I:S ratio | VDI 4630 recommends substrate-to-inoculum **below 0.5** (I:S > 2); the older baseline convention was **1:1**; conventions differ between protocols [CIT-0004] | `V-FULL` |
| Total solids | 5–20 % TS tested in food-waste AD, classified wet ≤10 %, semi-dry 10–20 %, dry ≥20 % [CIT-0006] | `V-FULL` |
| VFA | >4 g L⁻¹ VFA manifests as reduced biogas production [CIT-0010]; TVFA maxima up to ~29.6 g HAc/L measured at 20 % TS in co-digestion, alongside reduced specific methane yield [CIT-0012] | `V-META` |
| Ammonia | IC₅₀ of **19.0 g TAN/L** at 35 °C in one study; across studies 50 % inhibition is reported from **1.7 to 14 g/L** with thresholds of 1.1–11.8 g/L, a spread the papers themselves describe as unresolved [CIT-0014 `V-META`; CIT-0011] | `V-META` |
| Lipid/LCFA | Inhibition onset above **≈250 mg/L** for non-acclimated sludge and **≈400–450 mg/L** when acclimated [CIT-0015]; the food-waste enzyme paper's introduction cites profound inhibition at 0.2 g oleate/L and cessation at 0.5 g/L [CIT-0007 excerpt] | `V-META` / `PARTIAL` |
| Feedstock exclusions | Jaipur hotel food waste contains egg shells, coffee grounds, tissue paper and bone, components with different physical/chemical behaviour that resist degradation [CIT-0028, `V-FULL`]. The simulator has **no** term for these; this is an explicit simplification, to be stated in report §9 | `V-FULL` |

### 3.1 A live contradiction worth keeping

Two retrieved studies disagree about high total solids in food-waste digestion:

- 5–20 % TS in mesophilic food-waste AD: three stable processes, **better** VS reduction and methane yield at
  higher TS [CIT-0006, `V-FULL`].
- 5–20 % TS in co-digestion: specific methane yield statistically indistinguishable across 5–15 %
  (278.8–291.7 NmL/g VS) and **reduced at 20 %** (259.8 NmL/g VS) [CIT-0012, `V-META`].

This is not resolved here, and should not be: the two positions are carried side by side as C-005 below, and the
simulator's TS response stays deliberately mild, with its sensitivity explored by the sweep.

---

## 4. Modelling practice: what the ML literature implies for this project

Retrieved machine-learning work on anaerobic digestion, used as **context for expectations, never as
performance targets**:

| Study | Reported outcome | Relevance |
|---|---|---|
| Industrial-scale co-digestion, four years of process data; elastic net vs random forest vs XGBoost [CIT-0021, `PARTIAL`] | Tree models kept out-of-sample R² **0.80–0.88** across time horizons; elastic net reached 0.85 at a one-day horizon and degraded with longer horizons | Nonlinearity helps, but **horizon** matters more than algorithm choice. This project's synthetic task has no horizon, a difference that must be stated, not glossed. |
| Straw + biochar AD, 100 samples, 15 inputs; RF vs XGBoost vs SVM [CIT-0022, `PARTIAL`] | RF best: R² **0.81**, RMSE 36.9; feature importance dominated by feeding load, biochar dose and biochar carbon content (65.7 % combined) | A low-hundreds-sample study is the *normal* size in this field, relevant to how much confidence any single train/test split deserves. |
| Full-scale digesters, 42 physicochemical parameters plus DNA/RNA data [CIT-0023, `PARTIAL`] | Models reached only *moderate* R² despite rich inputs; **models optimised for one digester did not transfer to others**; the authors estimate 150–200 samples would be needed for stable prediction | The most useful result in this table: even with real measurements, **transferability is the weak point**. Synthetic scores cannot be better than that on this dimension. |

**Implications for the modelling.** The model set is fixed up front (Dummy, Ridge, RandomForest,
HistGradientBoosting, MLP) and the retrieved literature does not justify adding more. It does justify two
choices: (a) report seed-to-seed spread, because the retrieved studies rarely do; (b) never present feature
importance as biological causality, the retrieved importance claims rest on real measurements this project
does not have.

---

## 5. Regional pass: India

| Finding | Status |
|---|---|
| Official programme figures: **≈12 million family-type biogas plants** is the estimated national potential (based on cattle-dung availability); **4.31 million** had been installed; the National Biogas and Manure Management Programme has run since 1981-82; an independent evaluation found 95.81 % of surveyed plants operational [CIT-0029, `PARTIAL`: Ministry of New and Renewable Energy FAQ page, retrieved via search index] | Official source; **context tier only.** |
| Independent review: India's total biogas production is ≈**2.07 billion m³/year** against an estimated potential of **29–48 billion m³/year**; ≈5 million family plants represent roughly 40 % of the MNRE 12-million estimate; family systems are 1–10 m³ biogas/day and are **cattle-manure based** [CIT-0030, `PARTIAL`] | Peer-reviewed review; **context tier only.** |
| Hotel food waste (Jaipur, India): pre-treated and digested in a 45-day batch assay at 37 °C with a **41 %** increase in cumulative biogas at 100 °C/10 min; the paper also notes that food waste is commonly dumped with municipal solid waste because segregation is lacking, and that India loses or wastes ≈40 % of produced food before consumption [CIT-0028, `V-FULL`] | The one **primary Indian food-waste AD source** in this pass. |

**The substantive regional finding.** India's installed household biogas base is built around **cattle dung**,
a substrate with very different solids, nitrogen and degradability characteristics from food waste
[CIT-0029, CIT-0030]. Household food-waste digestion is therefore not simply a scaled-down cattle-dung plant,
and the failure modes differ (see §6). This is a limitation statement, not a design claim.

**Language coverage.** Searches were run in English with Hindi/regional term variants attempted for the
food-waste/biogas intersection. The retrieved AD literature is
overwhelmingly English-language and dominated by Chinese, European and North American experimental work.
**This is a bias in the evidence base, not a property of the technology.** Note also that only **two** Indian
items were retrieved with usable locators, one of which is a government FAQ, the regional evidence base is
thin and is reported as thin.

---

## 6. Lived-practice layer (UGC, context tier only, decision D12)

Retrieved across **four platform classes** (requirement R-U1), used **only** to inform limitations and the
risk register, never as a source for a parameter value:

| Platform class | Source | Repeated pattern |
|---|---|---|
| Classic forum | permies.com biogas threads [CIT-0024] | Cold-climate expectations dominate: "at lower temperatures… at about 20 °C they pretty much stop"; digesters must be much larger than beginners expect |
| Reddit (r/Permaculture) | "has anyone had success creating their own biogas digester?" [CIT-0025] | Pressure-tightness/"leaks" named as the hardest build problem; ~25 °C quoted as a minimum; corrosion of burners and piping from water and H₂S |
| Reddit (r/Wastewater) | operator thread on digester heat loss [CIT-0026] | Professional practice: keep mesophilic digesters near 35–37 °C; ≈1 °C/day loss treated as a warning sign |
| Q&A site | ResearchGate question on heating digesters [CIT-0027] | The same temperature problem recurs in the professional Q&A layer |

**Searched but not found (absence recorded as evidence):** no imageboard, video-comment, or regional-language
community was found carrying substantive digester-operation discussion for this niche. Several classes
(Discord/Telegram publics, video comments) were not reachable with the available tools and are therefore
*absent from the map, not proven irrelevant*.

**Tiering rule applied.** UGC is context. It corroborates that **temperature control and gas-tightness are the
dominant real-world fragilities**: consistent with the sourced optimum bands, but no constant in the
parameter table rests on it. Anecdotes with commercial intent were not found in the retrieved threads; if any
had appeared, they would be labelled as such.

---

## 7. How deep the search went

| Layer | Reached? | Contents in this niche |
|---|---|---|
| L0 surface | Yes | "Biogas from food waste" explainers and review introductions. |
| L1 working knowledge | Yes | Standard parameter bands; BMP protocol conventions [CIT-0004]; feedstock characterisation [CIT-0003]. |
| L2 operator detail | Yes | TS regimes [CIT-0006], OLR/HRT bands [CIT-0010, CIT-0011], inhibition thresholds, I:S conventions, hotel-waste contaminants [CIT-0028]. |
| L3 contested/advanced | Yes | (a) TS optimum contradiction [CIT-0006 vs CIT-0012]; (b) fungal pre-treatment helps *or harms* by strain [CIT-0018/CIT-0019 vs CIT-0007]; (c) rate-versus-extent and window-dependence [CIT-0016 vs CIT-0028]; (d) ammonia thresholds spanning an order of magnitude [CIT-0014]. |
| L4 obscure/tribal | Partially | Hobbyist/farm-scale failure modes from four platform classes (§6). Not exhausted: language-specific and video-comment layers were not reachable in this pass. |
| L5 meta | Yes | **Publication asymmetry.** Reviews tabulate dramatic increases (up to +154 % in one retrieved table [CIT-0020]) while the clean null result (no change in ultimate potential, only in rate [CIT-0016]) sits in a paper whose title advertises stimulation. The retrieved review itself notes that a meta-analysis was not feasible because of heterogeneity across studies [CIT-0018, `PARTIAL`]. Positive cases are reported far more often than null or negative ones. |

**Leads opened and closed while reading.** Ten side questions came up; seven were answered well enough to stop
(RH-01 to RH-05, RH-09, RH-10), one is closed with residual uncertainty (RH-06), and two are still open: whether
OLR and HRT are separable in the simulated design (RH-07, needs the fitted models) and whether the small MLP
beats the tree models on this simulator (RH-08, needs the study runs). None was dropped silently.

---

## 8. What changed in my beliefs after this pass

| Prior before reading | After reading | Why |
|---|---|---|
| P-A = 0.30: sources support a food-waste-specific *A. oryzae* benefit | **0.40** | Food-waste pre-treatment evidence exists, and the closest study names *A. oryzae* itself (protease generator in a two-fungus consortium, +55.87 % [CIT-0007]); thermal pre-treatment of Indian hotel food waste adds +41 % [CIT-0028]. Against it: no single-organism food-waste study exists, and the opened review carries explicit null and negative findings for fungal pre-treatment [CIT-0009, CIT-0032]. A moderate increase with a live contrary branch. |
| P-B = 0.75: lipid inhibition with a threshold | **0.80** | Multiple independent reports of a threshold in the hundreds of mg/L, though the value varies by a factor of ~3–5 [CIT-0015]. |
| P-C = 0.15: synthetic ranking informs real-system ranking | **0.12** | The retrieved ML studies show real-system predictors dominated by time-series history and rich inputs, and even then models did not transfer between digesters [CIT-0021, CIT-0023]. The synthetic-to-real gap looks *larger* than assumed. |
| P-D = 0.55: the recommended setting survives ±5 % perturbation | **unchanged 0.55** | No evidence either way until the perturbation test is run. |

**Claims entered/updated in the claim graph:** C-002 (lipid inhibition, evidence now attached; confidence
raised), C-003 (*A. oryzae* → food waste, remains `unknown`, now with four adjacent sources recorded),
C-004 (pre-treatment effects are reported more often on rate than ultimate potential), C-005 (the TS optimum
is contested), C-006 (food-waste methane-potential magnitudes), C-007 (real-world AD models do not transfer
between digesters, with `counter_ids` linking the synthetic-circularity claim C-001).

---

## 9. What is still unknown

1. **No direct *A. oryzae*-on-food-waste study was found.** The project's literal two-stage hypothesis is
   unsupported by retrieved evidence; the pre-treatment factor stays an explicit assumption (F1 part-fires).
2. **The rate-versus-extent question is unresolved in the literature itself**, so the model must choose and
   defend which one the target represents (S-1 fixes the endpoint definition; the rate output is still open).
3. **Ammonia and LCFA thresholds are reported as bulk concentrations**, while the simulator's inputs are
   fractions. The conversion is a modelling decision with no direct source.
4. **Indian food-waste evidence remains thin**: one primary study (hotel waste, Jaipur) plus one official FAQ
   and one review; the two Indian sources that were surfaced without captured locators are listed as uncited
   leads in the ledger rather than cited.
5. **No anaerobic-digestion-specific agent skill exists** (re-checked this phase, local and web), so
   methodology continues to come from the general scientific-computing skills already inventoried.
6. **Full texts of four paywalled sources were not obtained** (CIT-0007, CIT-0008, CIT-0011, CIT-0012 are
   `V-META`; CIT-0015, CIT-0018, CIT-0019, CIT-0020, CIT-0021, CIT-0022, CIT-0023 are `PARTIAL`). The access
   ladder attempts are noted as they come up. The report may cite these for context but
   **must not** attribute a load-bearing simulated range to a `PARTIAL` source.
7. **Process failure found and corrected:** several leads were captured without locators during the first
   search sweep; three were recovered (CIT-0018–CIT-0023 families) and the rest are recorded as uncited leads
   and they are listed at the end of `docs/references.md` rather than cited from memory.

---

## 10. Sources

Full references, retrieval routes and verification statuses: `docs/references.md`. Load-bearing anchors, CIT-0003 (food-waste characterisation), CIT-0004 (BMP unit
convention; basis of decision D4), CIT-0006 (total solids, `V-FULL`), CIT-0007 (*Aspergillus* consortium
pre-treatment of food waste), CIT-0009 (opened review), CIT-0010/CIT-0011 (operating parameters), CIT-0014
(ammonia), CIT-0015 (LCFA), CIT-0016 (rate versus extent), CIT-0028 (Indian hotel food waste, opponent and
supporter evidence in one paper).
