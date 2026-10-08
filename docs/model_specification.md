# Model notes: the simulator

These notes fix the implementation: the equations, the constants, the data split, the models, the metrics
and the sensitivity grid. Every constant is either sourced with a citation or labelled **ASSUMPTION FOR
SIMULATION** with a range. Nothing here is a claim about a real digester.

## 1. What the simulator is, in one paragraph

`src/simulate_data.py` computes a **deterministic, closed-form, bounded model** of a two-stage
food-waste-to-methane concept, then add **declared multiplicative noise**. The deterministic part is a chain of
permissive factors: a composition-derived ceiling, a pre-treatment availability/loss pair, a first-order rate
constant that converts to a window-completeness fraction, two inhibition terms (lipid/LCFA and ammonia), a mild
loading factor and a retention washout factor. Every constant is either sourced (with a citation) or labelled
**ASSUMPTION FOR SIMULATION** with a sensitivity range. Nothing here is a claim about a real digester; the
output is a **simulated** quantity reported in the BMP unit convention (decision D4).

---

## 2. Inputs and their tiers

The practitioner review (§"practitioner") made the point that most of the variables an
optimiser would like to set are **laboratory quantities** that a household or small-farm operator cannot
measure. The specification therefore splits every input into three tiers, and the study reports the optimiser's
recommendation **separately for each tier**.

| Tier | Variables | Who can set it |
|---|---|---|
| **C1: controllable at small scale** | feed composition (via what is fed: C/P/L fractions), water addition (→ total solids), temperature, pre-treatment duration, pre-treatment temperature, feed rate (→ OLR) | an operator with a thermometer and a bucket |
| **C2: laboratory-only** | pH (as a controlled setpoint), hydraulic retention time, inoculum-to-substrate ratio | requires monitoring and control equipment |
| **C3: observed, not chosen** | realised pH, stability indicator | consequences of tier C1/C2 choices |

**Rule:** the optimiser will be run twice, once over **C1 ∪ C2** (the "laboratory" recommendation) and
once over **C1 only** (the "achievable at home" recommendation), and both will be reported, with the
difference stated plainly. No recommendation may be presented without its tier label.

---

## 3. The data-generating process

### 3.1 Inputs (scenario level)

| Symbol | Column | Range | Class | Cite / assumption note |
|---|---|---|---|---|
| c | `carb_fraction` | 0.45 – 0.74 | `direct` (band is a modelling choice inside the sourced 12–74 % spread) | CIT-0008, CIT-0003 |
| p | `protein_fraction` | 0.05 – 0.25 | `direct` | CIT-0008, CIT-0003 |
| l | `lipid_fraction` | 0.02 – 0.30, computed as 1 − c − p | `direct` | CIT-0008, CIT-0009 |
| TS | `total_solids_pct` | 5 – 20 | `direct` | CIT-0006 (`V-FULL`), CIT-0012 |
| T | `temperature_c` | 20 – 60 | `direct` | CIT-0010, CIT-0011, CIT-0028 |
| pH_s | `ph_setpoint` | 5.5 – 8.5 | `direct` | CIT-0010, CIT-0011 |
| OLR | `olr_kg_vs_m3_d` | 0.5 – 6.0 | `direct` | CIT-0011 |
| HRT | `hrt_days` | 10 – 40 | `direct` | CIT-0010 |
| I | `inoculum_ratio` | 0.5 – 4.0 (g VS inoculum per g VS substrate) | `analogous`; basis declared | CIT-0004 |
| t | `pretreatment_hours` | 0 – 96 | `assumption` (scaling choice) | parameter table P1 |
| T_p | `pretreatment_temp_c` | 25 – 35 | `assumption` | CIT-0005 (context) |

**Latent, scenario-level, never written to the model-facing CSV** (leakage guard, §5):

| Symbol | Meaning | Distribution |
|---|---|---|
| R | pre-treatment asymptotic net response factor | 0.70 – 1.60, sampled as 1 + (U − 0.5)·0.90 truncated to the range, mean 1.00 |
| ℓ | asymptotic degradable-mass loss | Uniform(0.00, 0.20) |

### 3.2 Derived quantities

```
VS_slurry = TS/100 × 0.85 × 1000 # g VS per L of slurry; VS/TS = 0.85 from CIT-0003 (measured 83–87 %)
g(t) = 1 − exp(−t / 36 h) # pre-treatment progress; ASSUMPTION (τ = 36 h)
avail = 1 + (R − 1) × g(t) # availability multiplier ∈ [0.72, 1.56] at t = 96 h
loss = ℓ × g(t) # degradable-mass loss fraction ∈ [0, 0.20]
C_LCFA = l × VS_slurry × η # g LCFA per L, η = 0.012, ASSUMPTION (see §4)
TAN = 0.16 × p × VS_slurry × 0.70 # g N per L; 0.16 = protein N fraction, 0.70 = release, ASSUMPTIONs
VFA_stress = clip( (OLR/3.0) × (1 + 0.6·(l/0.30)) × (1 + 0.4·(p/0.25)) − 1 , 0, 1 )
pH_eff = pH_s − 0.8 × VFA_stress # loading-driven acidification; ASSUMPTION
ph_measured = round(clip(pH_eff + N(0, 0.05), 5.5, 8.5), 1) # what the operator reads
```

### 3.3 The yield equation

```
ceiling(c,p,l) = β × (c·0.415 + p·0.496 + l·1.014) × 1000 # mL CH4 / g VS
ceiling_eff = ceiling × avail × (1 − loss)
k = 0.18 × f_T(T) × f_pH(pH_eff) × f_LCFA × f_TAN × avail^0.7 # 1/day
r = 1 − exp(−k × min(30, HRT)) # window completeness
washout = clip((HRT − 6)/6, 0, 1)
yield = ceiling_eff × r × f_LCFA × f_TAN × f_load × washout # mL CH4 / g VS
```

with the permissive factors (each ∈ (0, 1]):

```
f_T(T) = max( exp(−½((T − 33.5)/10.0)²), 0.98 · exp(−½((T − 55.0)/6.5)²) )
f_pH(pH) = exp( −(d/0.7)² ) where d = max(0, 6.8 − pH, pH − 7.2)
f_LCFA = 1 / (1 + (C_LCFA/1.2)²)
f_TAN = 1 / (1 + (TAN/6.0)²)
f_load = exp(−½((OLR − 2.5)/1.8)²) · exp(−½((TS − 12)/10.0)²)
```

**Two deliberate structural rules (both are anti-double-counting guards):**

1. **One factor, one channel.** Temperature and pH enter **only** through the rate constant `k`. The two
 inhibitors and the loading factor enter **only** as direct multipliers on the yield. `HRT` enters **only**
 through the window term `min(30, HRT)` and the washout factor, never twice.
2. **The pre-treatment is the one deliberate exception:** it acts on **both** channels, on the ceiling
 (`avail`, `(1 − loss)`) and on the rate (`avail^0.7`). This is the dual-channel rule, and it is what makes the
 rate-versus-extent question (C-004) visible in the output instead of hidden in the assumption.

### 3.4 Secondary outputs

```
methane_fraction = clip(0.50 + 0.65·l + N(0, 0.01), 0.45, 0.75)
biogas_yield = yield / methane_fraction
stability = VFA_stress # 0 = stable, 1 = strongly stressed
```

`stability` is an **internal construct**, not a measurement, and is never reported as one.

### 3.5 Noise model

```
log_yield_model = log(yield) + a_scenario + a_replicate
a_scenario ~ N(0, 0.04²) # batch-to-batch difference, shared by a scenario's replicates
a_replicate ~ N(0, 0.05²) # within-scenario replicate scatter
final_yield = round(clip(exp(log_yield_model), 0, 600), 1)
```

Deliberate consequences: the noise is **visible** (coefficient of variation ≈ 6 %), and two scenarios with
nearly identical settings still produce different numbers. Because the split is grouped by scenario (§11), the
shared `a_scenario` term cannot leak between splits.

### 3.6 Rounding and missingness (realism; makes the leakage guards testable)

- Recorded inputs are rounded as a real instrument would: `ph_measured` to 0.1, `total_solids_pct` to 0.5,
 `temperature_c` to 0.5 °C, `olr_kg_vs_m3_d` to 0.1.
- **2 %** of `ph_measured` and **1.5 %** of `temperature_c` values are set to missing (MAR, independent of the
 target). This exists so that imputation is genuinely required and the "fit on train only" test (D-PRE) has
 something to catch.

---

## 4. Constants, calibration and provenance

| Constant | Value | Class | Where it comes from |
|---|---|---|---|
| k_carb / k_prot / k_lip | 0.415 / 0.496 / 1.014 L CH₄ g⁻¹ VS | **ASSUMPTION** | Textbook stoichiometric potentials (Buswell-type). **Not retrieved this session**, so labelled an assumption with a ±15 % sensitivity range. Their *blend* is what matters, and the blend is calibrated below. |
| β (biodegradability) | 0.95 | **ASSUMPTION, calibrated** | Chosen so the reference configuration lands inside the **measured** food-waste band 348–435 mL CH₄/g VS [CIT-0003]. Sensitivity 0.85–1.00. |
| k_ref | 0.18 d⁻¹ | **ASSUMPTION, calibrated** | Chosen so a favourable 30-day run is ≈95–99 % complete and a 20 °C run is ≈40 % complete (practitioner reports of near-stall at ~20 °C, §6 of the review). Sensitivity 0.10–0.25. |
| σ_T mesophilic | 10.0 °C, centred 33.5 | **ASSUMPTION** | Width not sourced; the *centre* is sourced (CIT-0010). Sensitivity 7–14. |
| σ_T thermophilic | 6.5 °C, centred 55.0, amplitude 0.98 | **ASSUMPTION** | Centre sourced (CIT-0010, CIT-0011). |
| pH plateau / decay scale | [6.8, 7.2] / 0.7 pH units | plateau **sourced** (CIT-0010); decay **ASSUMPTION** | |
| OLR centre / scale | 2.5 / 1.8 kg VS m⁻³ d⁻¹ | **ASSUMPTION** | Inside the tested 1–4 range (CIT-0011); shape unsourced. |
| TS centre / scale | 12 % / 10 pp | **ASSUMPTION: deliberately mild** | The high-solids direction is **contested** (claim C-005: CIT-0006 vs CIT-0012). A single-peaked mild curve is the neutral default; the sensitivity grid (§14) runs three alternative TS shapes instead of pretending the answer is known. |
| η (LCFA partition) | 0.012 | **ASSUMPTION, calibrated** | Calibrated so that high-lipid feed at high TS lands in the reported LCFA-inhibition zone (> 400 mg/L [CIT-0015]) while a low-lipid feed at low TS does not. Range 0.005–0.030, a first-order driver, swept in §14. |
| C_LCFA half-saturation | 1.2 g/L | **ASSUMPTION informed by** CIT-0015 (onset ≈250–450 mg/L) | The *onset* is sourced; the Hill shape (n = 2) is not. |
| Protein N fraction / release | 0.16 / 0.70 | **ASSUMPTION** | Standard protein nitrogen fraction; release fraction invented. |
| TAN half-saturation | 6.0 g/L | **ASSUMPTION informed by** CIT-0014 | Within the reported 1.7–14 g/L band for 50 % inhibition; the retrieved IC₅₀ of 19.0 g/L sits above it, and the conflict is carried rather than resolved. |
| VFA stress weights | OLR/3.0, 0.6·(l/0.30), 0.4·(p/0.25) | **ASSUMPTION** | An internal construct; anchored on the report that > 4 g/L VFA reduces biogas (CIT-0010) and that instability appears at higher OLR (CIT-0011). |
| pH drop per unit stress | 0.8 pH units | **ASSUMPTION** | Chosen so maximum stress lands the reactor at ≈6.2, inside the "acidification below ≈6.5" description (CIT-0010). |

### 4.1 Calibration anchors (specification-validation arithmetic, computed before freezing)

These are hand-arithmetic checks of the equations above, run in a scratch session (**not** project code, and
**not** a data generation). Their purpose was to catch an absurd specification before the simulator was built.

| Configuration | Inputs | Modelled yield (mL CH₄/g VS) |
|---|---|---|
| Reference favourable | c 0.77, p 0.15, l 0.08, TS 12, 33.5 °C, pH 7.0, OLR 2.5, HRT 30, I 4 | **412** |
| Typical mixed food waste | c 0.70, p 0.20, l 0.10, TS 12, 35 °C, pH 7.0, OLR 2.5, HRT 30, I 2 | **399** |
| Low-lipid, high-carbohydrate | c 0.80, p 0.15, l 0.05, TS 8, 35 °C, OLR 2.0 | **370** |
| Lipid/protein-rich, mid operations | c 0.55, p 0.20, l 0.25, TS 15, 35 °C, OLR 3.0, HRT 20 | **349** |
| High lipid **and** high TS/OLR | c 0.65, p 0.05, l 0.30, TS 20, 37 °C, OLR 4.0 | **217** (inhibition-dominated) |
| Cold and acidic | 20 °C, pH 6.0, otherwise reference | **161** |
| Pre-treatment, harmful branch | R = 0.75, ℓ = 0.10, 96 h | **275** |
| Pre-treatment, neutral | R = 1.00, ℓ = 0.10, 96 h | **362** |
| Pre-treatment, beneficial branch | R = 1.30, ℓ = 0.10, 96 h | **466** |
| Pre-treatment at 24 h only | R = 1.30, ℓ = 0.10, 24 h | **437** (diminishing returns visible) |
| Held-out OOD family, mild | l 0.35, TS 24, 55 °C | **131** |
| Held-out OOD family, near edge | l 0.32, TS 22 | **201** |
| Mid-range operations, **across the whole simulated composition distribution** | TS 12, 35 °C, pH 7.0, OLR 2.5, HRT 30, I 2, no pre-treatment | p05 **388**, median **434**, p95 **490** |

**What the anchors establish:** (i) the central configurations land inside the measured food-waste band
(348–435 mL/g VS, CIT-0003), the calibration target; (ii) the pre-treatment term spans **275 → 466**
(± ~26 % around neutral), i.e. harmful, neutral and beneficial regimes are all reachable (falsifier F2 is
satisfiable by construction); (iii) the OOD family is low but **not degenerate** (no exact zeros that would
make metrics meaningless).

**Honest caveat on the upper tail (recorded now, not discovered later).** Under *optimal* mid-range operations
the simulated composition distribution reaches ≈490 mL/g VS at the 95th percentile, **above** the 348–435
band of the single measured anchor [CIT-0003]. That is expected from the construction, because lipid-rich
compositions carry a higher theoretical potential (the `k_lip` assumption) and the anchor composition is not
lipid-rich. The study reports the achieved distribution *against* the anchor and state that the upper tail is
a property of the assumed stoichiometry, not an observation. If a reviewer objects to the tail, the §14
sensitivity grid's β and k_lip sweeps are the pre-declared place where that objection is tested.

---

## 5. The leakage guard between ground truth and features

The latent factors `R` and `ℓ` **determine** the pre-treatment effect and therefore the target. They are
written **only** to `data/synthetic/latent_factors.csv` (for sensitivity analysis and teaching), never to the
model-facing `data/synthetic/foodwaste_biogas.csv`. A scenario-grouped split (below) then prevents the shared
noise term from crossing splits. Two tests enforce this: a column-denylist test and a group-overlap
test.

---

## 6. Scenario and replicate structure; the sampling design

- **500 scenarios × 8 replicates = 4,000 rows per seed** (decision D5), 5 fixed seeds, a **runtime trade-off,
 explicitly not statistical power**.
- Independent draws per scenario by **stratified (Latin-hypercube-style) sampling** over each range, so that
 the design carries **no built-in correlation** between decision variables.
- **Composition sampling.** The composition is sampled as a declared *distribution*, not a
 uniform box: `l ~ Triangular(0.05, 0.30, mode 0.15)`, then `c ~ Triangular(0.45, 0.74, mode 0.65)` truncated at
 `1 − l − 0.05`, then `p = 1 − l − c`, keeping draws with `p ∈ [0.05, 0.25]`. **Acceptance ≈ 64 %.**
 Resulting distributions: `c` mean 0.64 [0.47, 0.74]; `p` mean 0.18; `l` mean 0.18, median 0.18,
 p05 0.11, p95 0.27, i.e. a lipid-typical food waste, not a lipid-forced one.
- **Why not a uniform box (the first design check caught this).** A uniform draw over `c ∈ [0.30, 0.70]`,
 `p ∈ [0.05, 0.25]` with `l = 1 − c − p` is *nearly infeasible*: the simplex forces `c + p ≥ 0.70`, so 62 % of
 draws are rejected and the survivors are pushed to lipid ≈ 0.22 with structurally distorted marginals. The
 box was therefore replaced by the declared distribution above, whose carbohydrate band (0.45–0.74) stays
 **inside** the sourced spread rather than extending past it. 
- **Known, documented bias:** the simplex constraint makes the composition fractions negatively correlated
 (design check: r(p,l) = −0.55, r(c,p) = −0.48, r(c,l) = −0.48). This is structural, not a defect, but it must
 be reported: feature importances for the three fractions will be partly interchangeable, and no causal
 reading of them is permitted.
- **Design check (run before freezing; resolves R-E2):** across the 11 variables, the largest absolute
 correlation is **|r| = 0.55** (the structural protein–lipid pair). **Excluding composition pairs, the largest
 is |r| = 0.057** (TS vs pH, sampling noise). Specifically r(OLR, TS) = +0.035, r(I:S, OLR) = −0.002,
 r(HRT, OLR) = +0.027. **Result for R-E2: OLR/TS and I:S/OLR are non-redundant by design**; only the
 composition triple is collinear, for the structural reason above.

---

## 7. Outputs, units and the D4 guard rails

| Output column | Unit | Role |
|---|---|---|
| `simulated_methane_yield` | **mL CH₄ g⁻¹ VS at STP** | primary target |
| `simulated_biogas_yield` | mL g⁻¹ VS | secondary |
| `simulated_methane_fraction` | v/v | secondary |
| `simulated_stability_indicator` | 0–1 | secondary + optimiser constraint |

Guard rails: the internal computation is scale-free and the
unit is applied once, in one place, as a declared **scale adoption**; every artifact carries the `SIMULATED`
marker; the unit convention is cited to CIT-0004 separately from any simulated effect size; and every
report-level mention states that **no BMP protocol is implemented**.

---

## 8. Held-out out-of-distribution family

A separate family of **60 scenarios** is generated outside the support of the training design: lipid fraction
**0.30–0.38** (training support ≤ 0.30) and total solids **22–28 %** (training support ≤ 20 %), with other
variables inside their normal ranges. These scenarios are used **only** for the extrapolation check and are
never used for fitting, tuning or selection. Expectation recorded in advance: models should degrade here, and
the *size* of the degradation is the finding. Since the values lie outside the sourced ranges, the report must
label them as **outside the modelled range**, not as predictions about real feedstock.

---

## 9. Training and evaluation protocol

1. **Split:** scenario-grouped 70/15/15 (350 / 75 / 75 scenarios per seed). All 8 replicates of a scenario stay
 in one split. Group-overlap is asserted, not assumed.
2. **Preprocessing:** imputers, scalers and any encoding are fit on the training split only. Tuning happens
 inside train/validation. The test split is opened **once**, at the end, for the five seeds.
3. **Models (exactly five):** `DummyRegressor` (mean), `Ridge`, `RandomForestRegressor`,
 `HistGradientBoostingRegressor`, small `MLPRegressor`. No additions, no padding.
4. **Metrics:** R², MAE, RMSE, reported as **mean ± spread over the 5 seeds**. Intervals are **descriptive**
 (spread across seeds), not inferential; no confidence intervals are computed without stating assumptions.
5. **Plots:** predicted-vs-true, residual-vs-predicted, and a seed-spread plot. Feature importance is labelled
 **"what the model used",** never "what drives the biology".
6. **Baselines and controls:** the `DummyRegressor` is the floor; a **permuted-target negative control** is run to prove the pipeline cannot manufacture skill from noise.
7. **OOD:** report the same metrics on the held-out family of §8 and state the extrapolation limits.

### 9.1 Decision rules

| Question / falsifier | Rule as written now |
|---|---|
| **Q1** defensibility of inputs | Answered by the parameter table; re-checked by a redundancy test on the generated design. |
| **Q2** pre-treatment without assuming benefit | Satisfied if generated scenarios contain harmful (< 1), neutral (≈ 1) and beneficial (> 1) `avail` regimes with a documented harmful case, verified by a distribution test, not by inspection. |
| **Q3** transparent, nonlinear-enough ground truth | Nonlinearity is **audited, not asserted**: if Ridge reaches ≥ 95 % of the best tree's test R² (mean over seeds), the comparison is declared **uninformative** (F3) and no model ranking is reported. |
| **Q4** leakage avoidance | Group-overlap test + fit-on-train-only mutation test must both pass; otherwise the optimiser step is **blocked** (F4). |
| **Q5** falsifiers | Each of F1–F7 has an action; the report states, per falsifier, whether it fired. |
| **P-D** perturbation robustness | If the ±5 % perturbation changes the recommended region or drops it below the baseline, the recommendation is reported as **artefactual** and no "best recipe" is claimed (F5). |
| **Seed dependence** | If the mean ± spread of the best model overlaps the dummy baseline's spread, the apparent skill is reported as seed-dependent (F7). |

---

## 10. Optimiser specification

**Objective:** `simulated_methane_yield` only, the simulator-defined outcome. Nothing else is optimised.

**Decision vector:** the twelve inputs of §3.1 minus the derived/observed ones (`ph_measured`, stability).
Bounds are the ranges in §3.1. Composition fractions are parameterised as the first two components (the third
is `1 − c − p`), so "sums to one" holds by construction.

**Constraints (all enforced, not merely reported):**

| # | Constraint | Threshold | Why |
|---|---|---|---|
| C-a | mixture fractions sum to 1 | by parameterisation | required |
| C-b | all inputs inside the ranges of §3.1 | hard box | required |
| C-c | stability | `VFA_stress ≤ 0.35` | feasibility beyond yield |
| C-d | ammonia | `TAN ≤ 4.0 g/L` | feasibility beyond yield |
| C-e | realised pH | `pH_eff ∈ [6.5, 8.5]` | the reactor must not be acidified |
| C-f | retention | `HRT ≥ 12 days` | below this the washout factor collapses; a "winner" that washes out is not a winner |

**Three arms, all reported:**

1. **True-objective arm**: optimise the simulator itself. This is the *oracle*: impossible in reality, and
 included precisely to measure how much of the surrogate's apparent advantage is real.
2. **Surrogate arm**: optimise the trained model's prediction, then **re-evaluate the recommendation on the
 true simulator**. The gap between predicted and true yield at the recommendation is the
 **surrogate-exploitation metric**: the headline result of the optimisation section.
3. **Baseline arm**: the equal-thirds mixture at mid-range process settings (decision D6).

**Robustness:** ± 5 % perturbation of every decision variable (±5 % of range width for bounded variables),
re-evaluated on the true simulator; the recommendation is reported only with its perturbation behaviour.

**Optimiser implementation (decision D7 default):** SciPy `differential_evolution` with a documented seed, plus
a grid/random-search comparison. If SciPy were unavailable the grid search alone would be used; both are
subject to the same constraints.

---

## 11. Pre-declared sensitivity grid

The sensitivity sweep varies **exactly these** assumptions, one at a time, at the stated levels, and reports the resulting
change in the median yield and in the optimiser's recommendation. Nothing else is swept, so the sensitivity
analysis cannot be chosen after seeing results.

| # | Swept assumption | Levels |
|---|---|---|
| 1 | β (biodegradability) | 0.85 / 0.95 / 1.00 |
| 2 | η (LCFA partition) | 0.005 / 0.012 / 0.030 |
| 3 | LCFA half-saturation | 0.8 / 1.2 / 2.0 g/L |
| 4 | TAN half-saturation | 4.0 / 6.0 / 10.0 g/L |
| 5 | k_ref | 0.10 / 0.18 / 0.25 d⁻¹ |
| 6 | σ_T mesophilic | 7 / 10 / 14 °C |
| 7 | TS shape | single peak at 12 % / monotone increasing (CIT-0006's direction) / single peak at 20 % |
| 8 | pre-treatment response distribution | harmful-leaning (mean 0.90) / neutral (mean 1.00) / beneficial-leaning (mean 1.10) |
| 9 | noise scale | half / nominal / double |
| 10 | missingness rate | 0 % / 2 % / 5 % |

---

## 12. Pre-declared pipeline-validation controls

1. **Permuted-target control:** with the training targets shuffled, every model must fail (test R² ≈ 0 or
 negative). Success here would indicate leakage, not skill.
2. **Duplicated-row guard:** because inputs are rounded, near-duplicate rows exist; the test asserts that no
 two rows from different scenarios are closer than a stated tolerance *unless* they are in the same split.
3. **Oracle check:** the true-objective optimiser must beat the baseline on the simulator, otherwise the
 optimiser (not the models) is broken.

---

## 13. What this specification deliberately does not do

1. **No hydraulics or kinetics beyond one first-order constant.** OLR, HRT and I:S are *flat descriptors* of a
 digestion setting; the model has no reactor geometry, no mixing, no washout dynamics, no two-phase
 behaviour.
2. **No microbial community, no acclimation, no trace elements, no co-substrate.**
3. **No contaminants** (egg shells, bone, coffee grounds, tissue, real hotel-waste components, CIT-0028).
4. **No economics.** Cost, energy demand and labour are discussed qualitatively only, as
 **proxies**, never calibrated.
5. **No claim of transfer.** Everything here is about a simulator; the report must say so wherever a number
 appears.

---

## 14. Change protocol

- Any change to these notes is listed at the bottom of the file with its reason and the results it affects.
- A change that touches a research question, a falsifier or a decision rule is not made once results exist;
 it would invalidate the study rather than update it.
- What these notes have to justify on their own: every column in the generated CSV, every constant used,
 the noise model, the split rule, the five models, the metrics, the constraints and the sensitivity grid,
 each with a test.
