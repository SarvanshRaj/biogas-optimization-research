# Synthetic dataset: data dictionary

**Every value in this directory is SIMULATED.** Nothing here is a measurement, a BMP result or an
observation of a real digester. The files are produced by `src/simulate_data.py`, which implements the
frozen equations of `docs/model_specification.md` (SPEC_V1).

## Files

| File | Written when | Contents |
|---|---|---|
| `foodwaste_biogas_seed<SEED>.csv` | `python -m src.simulate_data --seed <SEED>` | the model-facing dataset, 8 rows per scenario |
| `latent_factors_seed<SEED>.csv` | same run | the latent pre-treatment factors, one row per scenario, **never** joined to the model-facing file. It now carries the same `data_provenance` / `simulator_version` per-row labels as the frame (added in Phase 3 wave F so that no published table is the unlabelled exception); `as_of` was already there |
| `metadata_seed<SEED>.json` | same run | provenance, simulator version, seed, the scale-adoption note and the "no BMP protocol" note |
| `foodwaste_biogas_ood_seed<SEED>.csv` | add `--ood` | the held-out family (section 8 of SPEC_V1), only for the extrapolation check |

Regenerate everything deterministically:

```bash
python -m src.simulate_data --all-seeds --ood --outdir data/synthetic
```

The generator is a pure function of the seed: the same seed and the same pinned dependency versions
reproduce the same bytes. Five fixed seeds (`11, 23, 37, 41, 59`) are used for the study. The rule for
committing the files was recorded before they existed and measured against the actual run: five seeds plus
their held-out families are **9.6 MB**, under the declared 10 MB threshold, so Phase 4 commits them (the
`.gitignore` lines are removed at that point). Phase 3 runs wrote their files to a temporary directory and
committed none.

## Design (why the files look the way they do)

- **500 scenarios × 8 replicates = 4 000 rows per seed.** The row count is a runtime trade-off chosen for
  this study, explicitly **not** a statement about statistical power, and never presented as an
  experimental sample size.
- **Scenarios, not samples.** A scenario is one simulated feedstock/process configuration. Its eight
  replicates share a scenario-level noise term, which is why the split is grouped by `scenario_id`.
- **Split integrity.** `train` / `validation` / `test` labels are assigned per scenario, so every row of a
  scenario lives in exactly one split. Overlapping scenarios between splits would leak the shared noise
  term. A held-out family (`split == "ood"`) extends lipid fraction to 0.30–0.38 and total solids to
  22–28 %, outside the training support; it is never used for fitting or tuning.

## Columns

Roles: **ID** (bookkeeping), **C1/C2/C3** (input tiers from the optimisation decision S-7), **diag**
(diagnostic quantities carried for teaching and sensitivity work, a model may not use them), **out**
(outputs), **meta** (labelling).

| Column | Unit | Role | Notes |
|---|---|---|---|
| `scenario_id` |, | ID | `S00000…`; the grouping key for the split |
| `replicate_id` |, | ID | 0…7 within a scenario |
| `seed` |, | ID | the seed of the run |
| `split` |, | ID | `train` / `validation` / `test` / `ood` |
| `carb_fraction` | fraction | C1 | carbohydrate fraction of the mixture, ≥ 0.45 |
| `protein_fraction` | fraction | C1 | protein fraction; the three fractions sum to 1 exactly |
| `lipid_fraction` | fraction | C1 | lipid fraction; ≥ 0.05 |
| `ph_setpoint` | pH | C2 | the value that was *set*; the realised value is `ph_measured` |
| `total_solids_pct` | % wet mass | C1 | slurry total solids, **not** ambient relative humidity |
| `temperature_c` | °C | C1 | digester temperature; 1.5 % of values are missing on purpose |
| `ph_measured` | pH | C2 | realised pH after loading-driven acidification; 2 % missing on purpose |
| `olr_kg_vs_m3_d` | kg VS m⁻³ d⁻¹ | C1 | organic loading rate |
| `hrt_days` | d | C2 | hydraulic retention time |
| `inoculum_ratio` | g VS g⁻¹ VS | C2 | inoculum-to-substrate ratio on a VS basis (decision S-3). **Deliberately has no effect on the simulated yield**: SPEC_V1 §13.1 treats it as a flat descriptor, so a model should learn ~zero importance for it, and that is the simulator's assumption, not a finding |
| `pretreatment_temp_c` | °C | C3 | ambient temperature of the pre-treatment step; **carried but not used by the equations** (SPEC_V1 §3.3) |
| `pretreatment_hours` | h | C1 | duration of the fungal pre-treatment step |
| `vs_slurry_g_per_l` | g VS L⁻¹ | diag | `TS/100 × 0.85 × 1000` |
| `ph_effective` | pH | diag | `ph_setpoint − 0.8 × VFA stress` |
| `c_lcfa_g_per_l` | g L⁻¹ | diag | bulk LCFA concentration (`η = 0.012` partition assumption) |
| `tan_g_per_l` | g N L⁻¹ | diag | total ammonia nitrogen from protein (0.16 N fraction, 0.70 release) |
| `f_lcfa`, `f_tan` |, | diag | the two Hill-type penalty factors (0–1) |
| `rate_constant_per_day` | d⁻¹ | diag | the first-order rate constant of SPEC_V1 §3.3 |
| `window_completeness` |, | diag | `1 − exp(−k × min(30 d, HRT))` |
| `simulated_methane_fraction` | v/v | out | `clip(0.50 + 0.65·l + N(0, 0.01), 0.45, 0.75)` |
| `simulated_methane_yield_ml_per_g_vs` | mL CH₄ g⁻¹ VS (STP) | **out (primary target)** | see the scale-adoption note below |
| `simulated_biogas_yield_ml_per_g_vs` | mL g⁻¹ VS | out | `methane yield ÷ methane fraction` |
| `simulated_stability_indicator` | 0–1 | out | internal VFA-stress construct, also an optimiser constraint. **Never a measurement** |
| `data_provenance` |, | meta | always `synthetic` |
| `simulator_version` |, | meta | `SPEC_V1` |
| `as_of` | date | meta | the date the file was produced |

## Latent file (never a model input)

| Column | Meaning |
|---|---|
| `scenario_id`, `seed`, `as_of` | keys and labelling |
| `pretreatment_response` | the asymptotic pre-treatment response factor `R` ∈ [0.70, 1.60]; < 1 is harmful, > 1 beneficial, 1 neutral |
| `degradable_mass_loss` | the asymptotic degradable-mass loss `ℓ` ∈ [0, 0.20] |
| `realised_availability` | `1 + (R − 1)·g(96 h)`, the availability actually acting at the sampled duration |

`R` and `ℓ` **determine** the target through the pre-treatment channel. They are therefore written to a
separate file: if they were in the model-facing CSV, any model could read the answer out of a column and
the exercise would be worthless. This is the leakage guard; the tests in `tests/` enforce it.

## Unit provenance: the one physical label in the project

`simulated_methane_yield_ml_per_g_vs` borrows the reporting convention of biochemical methane potential
(BMP) measurements, documented in CIT-0004 (Filer et al. 2019, *Water* 11(5):921). It is a **scale
adoption**, chosen because a dimensionless index would hide the comparison with the measured food-waste
band (348–435 mL CH₄ g⁻¹ VS, CIT-0003):

- the internal computation is scale-free; the unit is applied once, in one place, as a declared conversion;
- **no BMP protocol is implemented**: no inoculum pre-incubation, no 10 g VS L⁻¹ loading rule, no 30-day
  incubation constraint, no positive control, no SIR < 0.5 rule;
- the unit convention is cited separately from any simulated effect size;
- every artifact carrying the value also carries the `SIMULATED` marker and this note.

## Missing values

2 % of `ph_measured` and 1.5 % of `temperature_c` are set to missing, independently of the target, so that
imputation is genuinely required and so that the "fit on training data only" rule has something to catch.
Missingness is a deliberate design feature, not damage to the file.
