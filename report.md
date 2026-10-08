# A simulated two-stage food-waste-to-biogas study

**Author:** Sarvansh Raj, ISC Class XII, Lucknow, India. **Date:** 7 October 2026.
**Repository:** github.com/SarvanshRaj/biogas-optimization-research.
**Licences:** code MIT, documents CC BY 4.0.

This is a computational study. Everything in it comes from a simulator I wrote, not from a
laboratory, and it contains no procedure for building, growing or operating anything. Every number in
every table and figure is **SIMULATED**.

Two warnings belong at the top, because they decide how to read the rest.

1. A model trained on this data learns the assumptions inside my simulator. It does not learn how
   real food waste or a real digester behaves.
2. The optimiser searches the simulator, so its best mixture is a property of my equations. It is
   simulator-specific and it is not a real recipe.

---

## 1. Study question and scope

The idea I am studying has two stages. In the first, a fungus (*Aspergillus oryzae*) is given time to
break down food waste. In the second, the pre-treated waste is digested and methane is produced.
Whether the first stage helps is the question the wider project is really about, and the honest
starting position I fixed before doing any work is that it might help, might do nothing, or might
hurt. The published record contains all three outcomes.

This study covers three computational parts:

1. **Pre-treatment as a hypothesis.** I model it as a signed net effect, an availability gain minus
   a degradable-mass loss, over a range that includes harmful, neutral and beneficial values. It is
   never coded as an improvement.
2. **Digestion as a simplified model.** A product of bounded factors (composition-weighted methane
   potential, temperature, pH, loading, retention and two inhibition terms), clamped to a physical
   range, with declared noise.
3. **Optimisation under constraints.** A population-based search over mixtures and process settings,
   run separately for two tiers of controllability, with a perturbation test and a ten-assumption
   sensitivity sweep.

What the study does not do: it does not measure anything, grow anything, build anything or operate
anything. It does not claim a real biogas yield for any feedstock, it does not claim that
pre-treatment works, and it does not present synthetic model scores as evidence about real
digesters. The 2025 Sakura Science Exchange Programme project is not part of this work. That
programme ran with a mechanical prototype and real food waste, was cleared at the elimination stage,
and ended before any software stage. Nothing here extends it or reports its data.

### The five research questions

I fixed these before collecting any evidence.

| # | Question | How it was settled | Where to check |
|---|---|---|---|
| Q1 | Which inputs are defensible, and which are unsupported or redundant? | A provenance table gives every input a class (`direct`, `analogous` or `assumption`), a source and a sensitivity range. Ambient relative humidity is excluded for lack of support. Redundancy between OLR and total solids, and between the inoculum ratio and OLR, is tested rather than assumed: the largest non-composition correlation in the design is 0.057 | `docs/parameter_table.md`, `tests/test_simulate_data.py` (the correlation and documented-redundancy tests) |
| Q2 | How do I represent pre-treatment without assuming it helps? | A signed latent factor, uniform over 0.70 to 1.60 and centred on 1.00, so harmful, neutral and beneficial cases all occur. The sweep tests the direction explicitly at 0.90, 1.00 and 1.10 | `docs/model_specification.md` section 3.1, `tests/test_properties.py`, the sweep row `pretreatment_response` |
| Q3 | Is the ground truth transparent, bounded, reproducible and nonlinear enough for a model comparison to mean something? | The ground truth is a bounded product of documented factors with declared noise. Whether it is nonlinear enough is audited by rule F3 rather than asserted | `docs/model_specification.md` section 3, and section 7 of this report |
| Q4 | How does the split avoid leakage between near-duplicate rows? | Scenarios are the unit of splitting. All eight replicates of one scenario stay in the same split, and the two latent factors that generate the pre-treatment effect are never written to the model-facing file | `tests/test_preprocess_leakage.py`, `tests/test_ood_split_validation.py` |
| Q5 | What would falsify or weaken the assumptions? | Seven falsifiers (F1 to F7), each with an action fixed in advance. The verdicts are in sections 7 and 8 | `docs/preregistration.md` section 8, `results/decision_rules.json` |

The acceptance criteria were fixed before execution. If the ground truth turned out to be effectively
linear, the model comparison had to be called uninformative (F3). If the optimiser's recommendation
failed a small perturbation, it had to be reported as an artefact with no recipe claimed (F5). If a
model's skill depended on the seed, that skill could not be claimed (F7).

## 2. What the literature supports, and what it does not

The full pass is in `docs/literature_review.md` and `docs/references.md`, which lists 32
citations with a locator and a verification status for each. This section gives only the conclusions
that shaped the model.

Food-waste digestion is well measured in one respect that matters here: a food-waste batch gave 348
mL CH4 per gram of volatile solids at 10 days and 435 at 28 days, with about 73 % methane and 81 %
volatile-solids destruction (CIT-0003). Mesophilic digestion is usually reported best between 31 and
35 degrees Celsius, thermophilic between 50 and 60 (CIT-0010). The pH plateau is 6.8 to 7.2, with
acidification below about 6.5 (CIT-0011), and food waste has been tested at 1 to 4 kg VS per cubic
metre per day with VFA-driven inhibition at higher loading (CIT-0011). Lipid-rich substrate inhibits
above a threshold (CIT-0015, CIT-0007). Ammonia inhibition is reported with an IC50 as high as 19.0 g
TAN per litre at 35 degrees, while 50 % inhibition is reported anywhere from 1.7 to 14 g/L across
studies (CIT-0014). That spread is a finding in itself, and the wide penalty band in the simulator
reflects it rather than tidying it up.

One conflict is important enough to keep instead of resolving. One study reports better performance
up to 20 % total solids (CIT-0006), while another reports a reduction in specific methane yield at 20
% solids, from 278.8 to 291.7 NmL/g VS at 5 to 15 % down to 259.8 at 20 % (CIT-0012). Both stay in
the model as claim C-005, and section 8 measures what the choice costs. This turns out to be the
largest structural risk in the study.

The pre-treatment hypothesis is the weakest part of the evidence base, and I want to be direct about
it: no retrieved study applies pure *A. oryzae* to food waste and then digests that same waste (claim
C-003, status partial). The nearest evidence points in both directions. A consortium-based enzyme
preparation that names *A. oryzae* as its protease source raised food-waste biomethane from 335.3 to
between 423.5 and 522.6 mL/g VS in a single study, an increase of 27 to 56 % (CIT-0007). Thermal
pre-treatment of Indian hotel food waste raised cumulative biogas by 41 % over the control (CIT-0028).
Against that, a review states that fungal pre-treatment of agricultural biomass did not improve
biomethane yield and was less effective than other methods (CIT-0009), another finds the sign of the
effect reversing between fungal species on the same substrate (CIT-0032), and *A. oryzae* also
appears in the reverse role, grown on the volatile fatty acids that digestion produces (CIT-0033).
Biological pre-treatment is also criticised for the time it takes (CIT-0034). So the model carries
the hypothesis with a symmetric range and never as a benefit.

Two further cautions from the literature sit behind the design. Models trained on real full-scale
digester data have repeatedly failed to transfer between digesters even with rich inputs (CIT-0021,
CIT-0022, CIT-0023), which is why section 7 reports the held-out check so prominently. And the unit I
report in is a convention I adopted from an opened methods source (CIT-0004); no BMP protocol is
implemented here.

## 3. Assumptions and parameter table

Every numeric input is labelled. `direct` means a retrieved source states it for this kind of system,
`analogous` means a source supports it for a related system, and **ASSUMPTION FOR SIMULATION** means
it is my choice, with the range I swept it over. The full table with applicability notes is in
`docs/parameter_table.md`.

| Parameter | Value or range used | Unit | Basis | Uncertainty |
|---|---|---|---|---|
| Carbohydrate fraction | 0.45 to 0.74, triangular with mode 0.65 | fraction of VS | direct (CIT-0008) | checked over 0.20 to 0.80 in design tests |
| Protein fraction | 0.05 to 0.25 | fraction of VS | direct (CIT-0008, CIT-0003) | 0.03 to 0.30 |
| Lipid fraction | 0.02 to 0.30, computed as 1 minus c minus p | fraction of VS | direct (CIT-0008, CIT-0009) | inhibition tested through the LCFA terms |
| Total solids | 5 to 20 | % wet weight | direct (CIT-0006, CIT-0012) | both the peak position and the shape are swept |
| Digestion temperature | 20 to 60 | degrees C | direct (CIT-0010, CIT-0011, CIT-0028) | plateau width swept at 7, 10 and 14 |
| pH setpoint | 5.5 to 8.5 | | direct (CIT-0010, CIT-0011) | plateau half-width swept at 4, 6 and 10 |
| Organic loading rate | 0.5 to 6.0 | kg VS per cubic metre per day | direct (CIT-0011) | enters through the loading factor |
| Hydraulic retention time | 10 to 40 | days | direct (CIT-0010) | constrained to at least 12 in the optimiser |
| Inoculum-to-substrate ratio | 0.5 to 4.0 | g VS per g VS | analogous (CIT-0004), standard not retrieved | declared no-op in this simulator |
| Pre-treatment duration | 0 to 96 | hours | assumption, a scaling choice | literature spans minutes to weeks |
| Pre-treatment net effect | 0.70 to 1.60, centre 1.00 | dimensionless | **ASSUMPTION**, span anchored on (CIT-0007, CIT-0028, CIT-0018, CIT-0019, CIT-0009) | swept at 0.90, 1.00 and 1.10 |
| Pre-treatment progress constant | 36 | hours | **ASSUMPTION** | shape properties tested |
| LCFA partition and half-saturation | 0.012 and 1.2 | g per L, g/L | analogous (CIT-0015, CIT-0007) | both swept, at 0.005/0.012/0.030 and 0.8/1.2/2.0 |
| TAN half-saturation | 6.0 | g/L | analogous (CIT-0014) | provenance range 1.0 to 8.0 |
| Beta, the methane-potential factor | 0.95 | | **ASSUMPTION** | swept at 0.85, 0.95 and 1.00 |
| Rate constant | 0.18 | per day | **ASSUMPTION** | swept at 0.10, 0.18 and 0.25 |
| Digestion window | 30 | days | assumption inside the reported 10 to 25 day ideal band | provenance range 20 to 60 |
| Volatile solids to total solids | 0.85, measured 83 to 87 % | | direct (CIT-0003) | cross-check only |
| Noise, scenario and replicate | 0.04 and 0.05 on the log scale | | **ASSUMPTION** | swept at half, nominal and double |
| Missingness | 2 % of pH readings, 1.5 % of temperature readings | | **ASSUMPTION**, so imputation has real work | swept at 0 %, nominal and 5 % |

Two things follow from this table. The parameters the literature constrains properly, which are
composition, temperature, pH and total solids, are the ones with sources. The parameter that carries
the project's central hypothesis does not have a source for this system, so it is an assumption with
a symmetric range, and section 9 says so again.

## 4. The simulator

The simulator is `src/simulate_data.py`, written to the frozen specification in
`docs/model_specification.md`. It is a deterministic function of twelve inputs plus two latent
factors, with declared noise on top.

```
ceiling        = beta x (c x 0.415 + p x 0.496 + l x 1.014) x 1000     in mL CH4 per g VS
avail          = 1 + (R - 1) x g(t),  where g(t) = 1 - exp(-t / 36 h)
loss           = L x g(t)
k              = 0.18 x f_T(T) x f_pH(pH_eff) x f_LCFA x f_TAN x avail^0.7
r              = 1 - exp(-k x min(30, HRT))
yield          = ceiling x avail x (1 - loss) x r x f_LCFA x f_TAN x f_load x washout
```

The factors `f_T`, `f_pH`, `f_LCFA`, `f_TAN`, `f_load` and `washout` each sit between 0 and 1, so
every term can only reduce the yield. Two rules keep the channels separate. Temperature and pH act
only through the rate constant. The inhibitors and the loading factor act only as multipliers on the
yield, and retention time enters only through the window term and the washout factor, never twice.
Pre-treatment is the single deliberate exception: it acts on the ceiling through `avail` and on the
rate through `avail^0.7`. That is what makes the rate-versus-extent question (claim C-004) visible in
the output instead of hidden inside an assumption.

Noise is multiplicative and log-normal. Each scenario draws one term with sigma 0.04 that it shares
across its eight replicates, and each replicate adds its own with sigma 0.05. The coefficient of
variation works out at about 6 %, so the noise is visible, and two nearly identical scenarios still
produce different numbers. Recorded inputs are rounded the way an instrument would round them, and
2 % of pH readings and 1.5 % of temperature readings are set missing so that imputation has real work
to do. The final yield is clipped to the range 0 to 600 mL CH4 per gram of VS.

The target is `simulated_methane_yield`, the endpoint specific methane yield over the declared 30-day
window, in mL CH4 per gram of volatile solids at STP. The secondary outputs (biogas yield, methane
fraction, a stability indicator) come from the same calculation, and the stability indicator is an
internal construct used by the feasibility constraint. It is never reported as a measurement.

Generation is seeded. The five study seeds are 11, 23, 37, 41 and 59, fixed in advance, and two
identical commands produce identical files. That is tested, not assumed.

One defect in the specification is worth recording. When I re-derived the specification's own sanity
anchors in section 4.1 from its own equations in sections 3.2 and 3.3, five of the thirteen did not
reproduce: they moved by between 6 and
74 mL CH4 per gram of VS, with the pre-treatment family about 3 % high (claims C-009 and C-010,
`docs/known_issues.md`). I pinned the anchors as written and reported the divergence rather
than tuning the code to match. The headline anchor, 411.6 plus or minus 1.0 mL CH4 per gram of VS, is
the published yardstick this model is measured against, and it does not reproduce exactly.

## 5. Data, schema and split

The committed dataset is `data/synthetic/`, 21 files and 9,999,347 bytes. It holds five model-facing
CSV files of 500 scenarios by 8 replicates, which is 4000 rows each, five held-out families of 480
rows each, two latent-factor tables, metadata and a data dictionary. The sample size is a
computational choice made for runtime, not an experimental sample size, and it carries no
statistical-power claim.

The columns fall into five groups. Composition holds the carbohydrate, protein and lipid fractions,
which sum to one by construction because the third is derived. Process holds total solids,
temperature, the pH setpoint, loading rate, retention time and the inoculum ratio. Pre-treatment
holds the duration and the temperature of that step. One observed column, `ph_measured`, is what an
operator would actually write down: rounded to 0.1 and sometimes missing. The target column is the
simulated yield defined in section 4.

| Column group | Examples | Notes |
|---|---|---|
| Composition | `carb_fraction`, `protein_fraction`, `lipid_fraction` | sum to 1 ± 1e-9 by construction; the third is derived, so the split cannot be chosen freely |
| Process | `total_solids_pct`, `temperature_c`, `ph_setpoint`, `olr_kg_vs_m3_d`, `hrt_days`, `inoculum_ratio` | ranges in section 3 |
| Pre-treatment | `pretreatment_hours`, `pretreatment_temp_c` | the hypothesis variables |
| Observed | `ph_measured` (rounded, with missingness) | what an operator would actually record |
| Target | `simulated_methane_yield_ml_per_g_vs` | definition in section 4 |

The split is grouped by scenario, 70/15/15, which is 350, 75 and 75 scenarios per seed. Every
replicate of a scenario stays in one split, the test set is opened once per seed at the end, and
imputation and scaling are fitted on the training split only. Near-duplicate rows are checked so that
rounded inputs cannot straddle train and test. The composition fractions are structurally correlated
because they must sum to one: the protein-lipid correlation is about minus 0.55, and that is reported
rather than hidden.

The 60 held-out scenarios per seed sit outside the sampled ranges on purpose, with lipid fraction
from 0.30 to 0.38 against a training maximum of 0.30, and total solids from 22 to 28 % against a
training maximum of 20 %. They are used only for the extrapolation check and never for fitting,
tuning or choosing a model. Because those values lie outside the sourced ranges, they are labelled as
outside the modelled range and not as predictions about real feedstock.

## 6. Models and training

Five models, fixed in advance: a dummy regressor predicting the mean, Ridge, a random forest,
scikit-learn's histogram gradient boosting, and a small multilayer perceptron. There are no
additions, no padding and no post-hoc selection. Each is trained on the same grouped split with the
same preprocessing, tuned inside the training and validation parts only, and saved with a JSON
sidecar holding its configuration.

Three controls guard the protocol. With the training targets shuffled, every model must fail, and a
success there would mean leakage rather than skill. No two rows from different scenarios may be
nearly identical unless they share a split. And in the optimiser, the true-objective search must beat
an equal-budget random search, otherwise the search, not the models, is the broken part.

Metrics are R-squared, mean absolute error and root mean squared error, reported as mean and spread
over the five fixed seeds. The spread is descriptive, not an inferential confidence interval, and no
interval is reported without its assumptions. Feature importance is permutation importance on the
test split, and it is labelled as what the model used, never as what drives the biology.

## 7. Results

Simulated results from five seeds and 500 scenarios. All values come from `results/`.

| Model | Test R2, mean and spread | Validation R2 | Held-out R2, mean | Test MAE | Test RMSE |
|---|---|---|---|---|---|
| Dummy baseline | -0.0322 plus or minus 0.0158 | -0.0031 | -2.52 | 112.17 | 131.09 |
| Ridge | +0.4540 plus or minus 0.1143 | +0.5229 | **-0.59, the best of a bad set** | 69.93 | 94.91 |
| Random forest | +0.7785 plus or minus 0.0214 | +0.9899 | -3.87 | 39.03 | 60.63 |
| Gradient boosting | **+0.8124 plus or minus 0.0390** | +0.9936 | -3.27 | 36.74 | 55.56 |
| MLP, small | +0.6947 plus or minus 0.0817 | +0.9199 | -5.23 | 52.53 | 70.56 |

Rule F3 did not fire. Ridge reached 55.9 % of the best tree model's test R-squared, well under the 95
% threshold, so the ground truth is genuinely nonlinear and the comparison is informative about the
simulator. Rule F7 did not fire either: the winner's spread does not overlap the dummy's. So a ranking
is allowed, and it is that the gradient-boosted trees win inside the sampled range, the small network
is second among the nonlinear models and the least stable, and the forest is close behind.

The held-out check is the most useful result in the study. Held-out R-squared is negative in 24 of the
25 model-seed combinations, and every model's five-seed mean is negative. The single exception is Ridge
at seed 59, plus 0.51, and it is exactly the kind of lone cell that a five-seed mean hides, so the mean
is what I report. The best model inside the sample is not the best extrapolator: the least bad mean
belongs to Ridge at minus 0.59, still worse than predicting the mean. These models interpolate inside
the region they saw and fall apart outside it, which is the extrapolation limit stated as a number
rather than as a warning.

On feature importance, the models lean hardest on `ph_measured`, with permuted importance 0.92 for
boosting and 1.05 for the network, then on loading rate at 0.55 and 0.67, then on total solids at
0.067 and 0.075. `ph_measured` is a derived column, computed as the setpoint minus a loading-driven
acidification term, so the models are leaning on the simulator's acidification channel. That is a
statement about how the simulator is built.

Four figures live in `results/figures/`, each marked SIMULATED: predicted against true, residuals
against predicted, permutation importance, and the spread across seeds. The residuals are structured
rather than noise-like, which fits the extrapolation finding.

## 8. Optimisation

The optimiser maximises the simulator's endpoint yield and nothing else. The mixture fractions sum to
one by parameterisation, every variable stays inside its declared range, and feasibility goes beyond
yield: the stability indicator must stay at or below 0.35, TAN at or below 4.0 g/L, effective pH
between 6.5 and 8.5, and retention time at least 12 days. Violations are penalised by 10,000 per unit,
which dwarfs any achievable yield, and the result is then re-checked by an assertion that raises
rather than warns.

Every run is reported in two tiers. Tier C1 is what an operator with a thermometer and a bucket could
set. Tier C1+C2 adds laboratory-only controls, which here means the pH setpoint and the retention
time. Each tier runs four arms: the true-objective oracle, an equal-budget random search as a fairness
control, the declared equal-thirds baseline, and one surrogate arm per trained model.

| Arm | Tier C1 | Tier C1+C2 | Note |
|---|---|---|---|
| Oracle, true objective | **513.92** | **513.76** | feasible, and it beats the random search |
| Equal-budget random search | 439.19 | 439.92 | control 3 of the specification passes |
| Declared baseline, equal thirds | 313.70 | 313.70 | **infeasible**: stability 1.000 against a limit of 0.35, pH 6.20 against a floor of 6.5. The comparator is its pre-declared feasible projection, 365.8, which the oracle beats by about 40 % |
| Gradient boosting | 429.16, promised 510.66 | 429.66, promised 509.43 | gap of 81.5 and 79.8 |
| Random forest | 420.17, promised 496.74 | 421.16, promised 517.43 | gap of 76.6 and 96.3 |
| MLP | 343.99, promised 524.19 | 360.74, promised 584.13 | gap of 180.2 and 223.4 |
| Ridge | 212.08, promised 312.17 | 25.23, promised 430.17 | gap of 100.1 and 404.9, and its true yield is below the baseline |
| Dummy | 314.21, promised 115.15 | 17.99, promised 115.15 | the only arm wrong in both directions, by 199.1 under and 97.2 over |

Two things stand out. First, every surrogate except the dummy over-promises its own recommendation.
When the optimiser pushes a model toward its favourite corner, that is exactly where the model is most
optimistic, which is the classic surrogate-exploitation failure and the reason a perturbation check is
not optional. Second, the tier labels matter: adding laboratory-only variables does not raise what is
achievable, since the oracle barely moves, but it gives the surrogates more room to over-promise.

Rule F5 fired on the oracle itself, in both tiers. Only 26 % of perturbations in tier C1 and 32 % in
tier C1+C2 remain feasible after a 5 % change, and the average perturbed yield, 505.4 and 504.9, sits
below the recommended point of 513.9 and 513.8. The optimum is pressed against the stability
constraint, so a small change in the settings pushes it out of the feasible region. The rule I wrote
in advance says what to do when this happens, so the optimum is reported as an artefact of the
simulator, and no best recipe is claimed anywhere in this report. Anyone can see that the optimiser
will exploit whatever the equations allow, and here it did.

### Sensitivity of the ten assumptions

The sweep is exactly the grid frozen in section 11 of the specification: ten assumptions, three
levels each, nothing else. Each row is measured against that assumption's own nominal level. The
nominal level of every assumption reproduces the committed dataset byte for byte, which is tested.

| Assumption | Level | Median yield change | Tier C1 recommendation change |
|---|---|---|---|
| Total-solids shape, the contested direction | monotone increasing | **-65.2 %** | **-32.1 %** |
| Total-solids peak position | 20 % solids | -24.8 % | -11.7 % |
| Rate constant | 0.10 per day | -34.3 % | -5.4 % |
| LCFA partition | 0.030 | -24.1 % | -17.1 % |
| pH plateau half-width | 4 | -23.1 % | -0.8 % |
| LCFA half-saturation | 0.8 g/L | -3.9 % | -7.3 % |
| Temperature plateau width | 7 degrees | -10.5 % | -0.2 % |
| Beta | 0.85 | -10.5 % | -10.3 % |
| Rate constant | 0.25 per day | +22.3 % | +0.4 % |
| pH plateau half-width | 10 | +16.8 % | -0.3 % |
| Pre-treatment response | 0.90 and 1.10 | -7.7 % and +9.8 % | **0.0 % and 0.0 %** |
| Noise scale | half and double | -2.1 % and +3.4 % | 0.0 % |
| Missingness | 0 % and 5 % | 0.0 % | 0.0 % |

Three readings, and I will keep them short. The recommendation is far more robust than the average
level: the rate constant moves the mean yield by a third while moving the recommended settings by 5 %,
and a report that mixed those two up would misstate the study. The largest structural risk is the
contested total-solids direction, which is exactly where the sources disagree, and it costs 65 % of
the mean yield and a third of the recommendation. Finally, the pre-treatment response factor moves the
level by 8 to 10 % and moves the recommendation not at all, because it multiplies everything
uniformly. That is the mechanical reason this sweep cannot answer whether pre-treatment helps. Q2 is
answered by the data containing harmful, neutral and beneficial cases, which a distribution test
checks, not by this grid.

## 9. Limitations

1. **The circularity is real and cannot be removed.** The target is defined by my own equation, so a
   model that scores well has learned my assumptions (claim C-001). That is why every score here is
   labelled SIMULATED and why the conclusions are about the pipeline rather than about digesters.
2. **Nothing here is validated against reality, and real transfer is known to be hard.** Full-scale
   digester models have repeatedly failed to transfer between digesters (claim C-007).
3. **The pre-treatment hypothesis is untested.** No retrieved study applies pure *A. oryzae* to food
   waste and then digests the same waste (claim C-003). The model represents the hypothesis; it
   cannot confirm or refute it, and section 8 shows it could not even rank on it.
4. **The contested total-solids direction is the largest structural risk** (claim C-005), at minus
   65.2 % on the mean yield in the alternative form. The frozen choice is the optimistic one.
5. **Rate-versus-extent effects cannot appear.** Pre-treatment effects reported on the rate of
   production (claim C-004) would be invisible to a single endpoint yield with no rate descriptor.
6. **The inoculum-to-substrate ratio is a declared no-op** (claim C-011), so a model trained here will
   show almost no importance for it. That is a property of the simulator, not a finding about the
   ratio.
7. **The specification's own anchors do not all reproduce**: five of thirteen, by 6 to 74 mL CH4 per
   gram of VS (claims C-009 and C-010). Reported and pinned, not tuned away.
8. **The small network does not converge.** Re-fitting it on all five study seeds raised exactly one
   convergence warning per seed, five of five, and the same check reproduced the study's per-seed test
   R-squared for the network: 0.7331, 0.7562, 0.5831, 0.6338 and 0.7673. It is reported as it is,
   second among the nonlinear models and the least stable, and the ranking does not depend on hiding
   the warning.
9. **The sample size is a runtime choice, not statistical power**, and the spread over seeds is
   descriptive rather than an inferential interval.
10. **The objective is cost-free by declaration.** Cost proxies are reported and never optimised. I
    declined to add a cost model because it would have optimised a second unvalidated quantity.
11. **A biochemical simulation cannot speak to real failure modes.** Sealing and leak integrity,
    moisture excursions, corrosive gas species, operator practice and seasonal temperature swings are
    outside the model's vocabulary. I surveyed community-reported issues across three platform classes
    as context only, and none of those figures became a constant. Section 11 is where the limits get
    their space, not the model.
12. **The optimiser exploits whatever is not physical.** By construction it will find the softest
    spots, and it did. Every best number in this report is a statement about the equations.

## 10. Reproducibility

These commands regenerate every committed artefact. The runtimes are what I observed on a 2 vCPU
machine.

```bash
python3 -m pip install --break-system-packages -r requirements.txt
ruff check src tests && mypy
pytest --cov=src --cov-branch --cov-report=term-missing         # 343 passed, 0 skipped, 100 % coverage
python -m src.simulate_data --all-seeds --ood --outdir data/synthetic
python -m src.evaluate --seeds 11,23,37,41,59 --n-scenarios 500 --ood-scenarios 60 --outdir results   # 2m18.6s
python -m src.optimize --seed 11 --n-scenarios 500 --models dummy,ridge,random_forest,hist_gradient_boosting,mlp \
  --perturbation-draws 200 --max-iterations 60 --population-size 15 --outdir results/optimisation      # 3m40.8s
python -m src.sensitivity --seed 11 --n-scenarios 250 --models ridge,hist_gradient_boosting \
  --max-iterations 20 --population-size 8 --perturbation-draws 20 --outdir results/sensitivity         # 8m49.4s
```

The environment was Python 3.11.2 with numpy 2.4.6, pandas 3.0.6, scikit-learn 1.9.1, scipy 1.17.1,
matplotlib 3.11.2, pytest 9.1.1, pytest-cov 7.1.0, hypothesis 6.168.5, ruff 0.16.10 and mypy 2.4.0.
The test suite ends at 343 passed, 0 skipped in 313.99 seconds, with 100 % statement and branch
coverage on the core modules, 1388 statements and 336 branches, and ruff and mypy clean.

`results/` holds 16 files and 610.0 KiB: the metrics per seed, the summary and held-out tables, the
decision-rule record, feature importance, run metadata, four figures, the optimiser's summary,
recommendations and metadata, and the 30-row sweep. `results/README.md` lists the same commands and
the analysis. Every CSV row is labelled `simulated: true` with the simulator version, and every figure
title carries the SIMULATED marker.

The model notes and the plan that govern the results were written before any result existed, and the
tests pin every constant they declare, so a drift in either is caught rather than trusted.

Four things about this environment should be stated rather than smoothed over. Sandbox restarts
flattened my local Git history twice, so the reconstruction is a labelled recovery commit and the
commit identifiers are local to that machine. The GitHub Actions workflow first executed on 8 October
2026, when it failed twice on problems that only appear on a clean runner: a `pytest` import path, and a
`mypy` error under the numpy 2.5 stubs on Python 3.12. Both are fixed in the tree, and the runs that
follow the fixes have not happened yet. Mutation testing was done by hand
only: four mutants in the final wave, all killed, with earlier waves recorded honestly, including one
mutant that survived and was then killed by a new test. And five written claims turned out wrong when
I re-measured them, and are corrected in place with the corrections visible: a mutation table whose
counts I had never observed, the file count and size of `results/`, two models' MAE and RMSE in the
first draft of this report, the byte size of the dataset, which I had recorded as 10,003,242 bytes
while the committed tree measures 9,999,347, and the sentence that every held-out R-squared is
negative, which holds for 24 of the 25 model-seed cells rather than all of them. The rule I took from
those five is in section 12: a number that appears in a document is copied from a command, never from
memory.

A re-run will reproduce the dataset, the evaluation and the sweep byte for byte on the same library
versions. The optimiser is stochastic in its search but seeded, and the study configuration reproduces
the numbers in section 8. Library upgrades may change floating-point details in the learned models,
and that is documented rather than papered over.

## 11. What I would do next

Four options, grouped in three tiers. None of them is a procedure, and this document contains none.
Anything physical in tier C would be carried out by qualified adults at an institution with the
required biosafety and engineering oversight, and my role there would stay computational. Each option
has a kill criterion fixed now, so that stopping is a decision made in advance rather than a failure
discovered late.

**Tier A, still computational.** The first option is to add an explicit rate and time dimension to
the simulator, so that a rate-only effect, the class of effect claim C-004 describes, becomes visible
instead of unrepresentable. I would kill it if no two retrievable sources share a substrate class,
temperature and measurement window closely enough to constrain a curve, in which case the honest
output is a note about why it cannot be done. The second option is to remove the structural
composition collinearity by re-parameterising and check whether the importance map becomes
interpretable. I would kill that if the new features cannot be mapped back to the three fractions a
reader understands, or if the change makes the simulator harder to falsify rather than easier.

**Tier B, evidence work with no laboratory at all.** I would run a synthesis of
reported effect sizes for fungal and thermal pre-treatment of food waste, recording substrate class,
operating conditions and measurement window, and stating in advance what would count as a pooled
estimate. The kill criterion is fewer than five studies reporting a comparable substrate class and
window; in that case I publish the map of what exists and why it cannot be pooled, and stop.

**Tier C, physical work under supervision only.** This is the option where the computational study
would define what needs to be measured, and the physical work would be proposed, approved and carried
out by qualified adults with biosafety oversight at an institution. I would not attempt it alone and
not from instructions in a school report. The kill criterion is the absence of supervision,
institutional approval or biosafety sign-off, or the absence of a frozen analysis plan before any
measurement starts. Those conditions are not negotiable, and without them the option does not start.

Without supervision, tiers A and B are what I would actually do, and they are where this project
already lives. Tier C is in this list so that the boundary is visible.

## 12. The study in plain words, and viva questions

### 12.1 What this project actually did

Food waste, when it breaks down without air, gives off a gas that is mostly methane, which is what a
biogas plant collects. Several kinds of bacteria do the work in steps. One idea is to give the waste
to a fungus first, so that the tougher parts break down before the bacteria get to work. I did not
grow any fungus. Instead I wrote a computer program that pretends to be the process, under rules I
fixed in advance, and then I asked ordinary machine-learning models to learn that pretend world. The
point was to test the method: can you build a study where a model's score actually means something,
where the pretend world is written down completely, and where the study's own claims can be checked
and even disproved?

Three results matter more than the accuracy figures.

The models learned the pretend world, not the real one. Inside the region they had seen, the best
model explained about 81 % of the variation. Outside it, the scores collapse: 24 of the 25 model-seed
combinations do worse than simply guessing the average, and the one that does not is a single seed that
the five-seed mean washes out. That is the honest boundary of what models like these can do.

The optimiser found a best mixture and then failed its own safety test. When I jiggled the
recommended settings by 5 %, only about a quarter to a third of the jiggles still satisfied the
stability rules. The plan I wrote before running anything said that if this happened, no best mixture
would be reported, so none is. A recipe would have been a property of the equations.

One assumption mattered more than the pre-treatment story. Changing the shape of the solids response
moved the average yield by 65 %, and that is exactly where the real literature disagrees with itself.
The pre-treatment effect, meanwhile, could move the average yield by 8 to 10 % but moved the
recommended settings by nothing at all. So this study cannot answer whether pre-treatment helps. It can
only show that a model like mine cannot rank mixtures on it. The scientific habit that mattered most
was writing down in advance what would count as failure, and then following through when it happened.

### 12.2 Ten viva questions with answers

**1. What is biogas, and which part of it matters here?**
Biogas is the gas produced when organic matter breaks down without oxygen. Its useful part is methane,
typically about 50 to 75 % in systems like this, because methane is what burns. My target is specific
methane yield, meaning methane per gram of volatile solids, because that is how the potential of a
feedstock is reported and because it removes the effect of carbon dioxide dilution.

**2. Why split the process into two stages?**
Because the stages do different jobs. Pre-treatment tries to make the waste easier to break down, and
digestion produces the methane. Splitting them lets me ask whether the pre-treatment helps instead of
hiding that question inside one number.

**3. What does SIMULATED mean in your project, and why does it appear everywhere?**
It means the data came from equations I wrote rather than from measurements. It appears everywhere so
that nobody can quote a number from this work as if a digester had produced it. A model trained on
simulated data learns the simulator's assumptions, and that is the most important limitation in the
whole project.

**4. Why exactly five models, and which one won?**
I fixed the five before any modelling: a dummy mean as the floor, Ridge as a linear model, a random
forest, gradient-boosted trees, and a small neural network. Fixing the list stops me from shopping for
a winner. Inside the sampled range the boosted trees won, with a test R-squared of about 0.81 plus or
minus 0.04. The network came second at about 0.69 and was the least stable, and Ridge reached about
0.45.

**5. What does R-squared mean, and why is a negative value not a bug?**
It compares a model with always predicting the mean. One is perfect and zero is as good as the mean,
so a negative value means the model is worse than the mean. That is the correct way to say the model
is useless in that setting. My held-out scores are negative in 24 of the 25 model-seed cases, and every
model's five-seed average is negative, which is why I report the extrapolation limit as a finding
instead of hiding it.

**6. What is a scenario-grouped split, and what would go wrong without it?**
Each scenario in my dataset is one feedstock setting, copied into eight replicate rows that share a
noise term. If I split rows at random, near-identical replicates would land in both training and test
and the test score would be inflated. That is leakage. So I split by scenario, keeping all eight
replicates together, and I test that no scenario appears in two splits.

**7. What did the optimiser maximise, and what extra constraints did you add?**
Only the simulator's yield. On top of that, the mixture fractions must sum to one, every variable
stays inside its allowed range, and I added feasibility rules beyond yield: stability below a
threshold, ammonia below a limit, pH inside a band, and retention time above a minimum. A recipe is
not useful if it only works when the process is about to fail.

**8. Why did you not report a best mixture, even though the optimiser found one?**
Because I fixed the rule before running it. If small changes of 5 % to the recommended settings break
feasibility or drop the yield, the recommendation must be called fragile and no best recipe may be
claimed. That is what happened: the optimum sits against the stability constraint, so about three
quarters of small perturbations fall outside the feasible region. Reporting it anyway would have been
exactly the over-claiming the rule existed to prevent.

**9. What is a sensitivity analysis, and what did yours show?**
It asks how much the answers depend on assumptions that are uncertain. I varied ten of them at three
levels each and measured the effect on both the average yield and the recommended settings. The
recommendation turned out much more robust than the average level, and the biggest single risk is the
contested total-solids direction, at 65 % of the mean yield. The pre-treatment factor moved the
average by 8 to 10 % but did not move the recommendation at all, which is the mechanical reason this
study cannot answer whether pre-treatment helps.

**10. If you could continue, what would you do, and what would you refuse to do?**
I would stay computational. I would add a rate and time dimension so that rate-only effects stop being
invisible, and I would run a proper synthesis of published pre-treatment effect sizes.
I would refuse to treat the optimiser's mixture as a recipe. I would also refuse to attempt any
physical work without qualified adult supervision, institutional approval and biosafety oversight.

### Where everything lives

| What you need | File |
|---|---|
| The model notes: equations, constants, constraints, decision rules | `docs/model_specification.md` |
| Literature, parameter provenance and the reference list | `docs/literature_review.md`, `docs/parameter_table.md`, `docs/references.md` |
| The anchor check and what did not reproduce | `docs/known_issues.md` |
| The tests | `tests/` (14 files) |
| Results and their catalogue | `results/`, `results/README.md` |
| The data and its dictionary | `data/synthetic/README.md` |
| The commands to reproduce the run | `results/README.md` |

Code is MIT (`LICENSE`). Documents and this report are CC BY 4.0 (`LICENSE-docs`).
