# results/: SIMULATED study output (Phase 4)

**Everything in this directory was produced by `src/simulate_data.py` (SPEC_V1), a simulator.**
No row here is a measurement, no recipe here has been built, and no number here describes real food
waste or a real digester. The marker `SIMULATED` is on every CSV row, every JSON payload and every
figure title for that reason.

## The three commands that produced this directory

```bash
# 1. models and metrics, five seeds x 500 scenarios, with the held-out family
python3 -m src.evaluate --seeds 11,23,37,41,59 --n-scenarios 500 --ood-scenarios 60 --outdir results

# 2. the optimiser, both tiers, all five models, at study size
python3 -m src.optimize --seed 11 --n-scenarios 500 \
    --models dummy,ridge,random_forest,hist_gradient_boosting,mlp \
    --perturbation-draws 200 --max-iterations 60 --population-size 15 \
    --outdir results/optimisation

# 3. the ten pre-declared assumptions x three levels (SPEC_V1 section 11)
python3 -m src.sensitivity --seed 11 --n-scenarios 250 \
    --models ridge,hist_gradient_boosting --max-iterations 20 --population-size 8 \
    --perturbation-draws 20 --outdir results/sensitivity
```

Runtimes on the 2-vCPU sandbox: 2m31s, 3m41s, 8m49s. The whole chain is deterministic; re-running
the commands reproduces these files byte for byte apart from the metadata timestamps.

## What is here

| Path | What it holds |
|---|---|
| `metrics_seed_level.csv` | one row per seed x model x split (validation, test), with R², MAE, RMSE, n |
| `metrics_summary.csv` | those rows collapsed to mean / std / min / max over seeds, with `n_seeds` and `n_finite` |
| `metrics_ood.csv` | the held-out family, scored by models that never saw it |
| `decision_rules.json` | rules F3 and F7, their thresholds, the numbers behind the verdicts, provenance |
| `feature_importance.csv` | permutation importance per model x feature, labelled "what the model used" |
| `run_metadata.json` | seeds, sizes, package versions and the scope note |
| `figures/` | predicted-vs-true, residuals-vs-predicted, seed spread, permutation importance |
| `optimisation/` | the three arms for both tiers, the perturbation reports and the F5 verdicts |
| `sensitivity/` | the ten-assumption sweep with its deltas and the sweep-scale note |

## Models on the untouched test split (mean ± spread over 5 seeds)

| model | test R² | validation R² | held-out R² |
|---|---|---|---|
| dummy (mean predictor) | −0.032 ± 0.016 | −0.003 | −2.52 |
| ridge | +0.454 ± 0.114 | +0.523 | **−0.59** |
| random_forest | +0.779 ± 0.021 | +0.990 | −3.87 |
| **hist_gradient_boosting** | **+0.812 ± 0.039** | +0.994 | −3.27 |
| mlp | +0.695 ± 0.082 | +0.920 | −5.23 |

**F3 does not fire** (ridge 0.454 is far below 95 % of the best tree's 0.812), so per the
pre-declared rule the comparison is *informative* and a ranking may be stated: gradient boosting
first, forest second, MLP third, ridge fourth, dummy last. **F7 does not fire**: the winner's range
across seeds [+0.775, +0.866] is nowhere near the baseline's [−0.044, −0.010].

Three readings that matter more than the ranking:

1. **Every model fails out of distribution, including the winner.** Held-out R² is negative in 24 of
   the 25 model-seed cells; the exception is ridge at seed 59 (+0.51), and every model's five-seed mean
   is negative. The in-distribution winner (boosting, mean −3.27) is *not* the best extrapolator, ridge
   is (mean −0.59), and even that mean is worse than predicting nothing. This is the extrapolation limit, stated as a
   number: the models interpolate inside the sampled region and fall apart outside it.
2. **The important features are the simulator's structure, not biology.** Permutation importance is
   dominated by `ph_measured` (0.92 for boosting, 1.05 for the MLP), then OLR, then total solids.
   `ph_measured` is a *derived* column (setpoint minus loading-driven acidification), so the models
   are leaning on the acidification channel, the same channel whose absence from the frozen §4.1
   anchor table caused the divergence documented in `docs/known_issues.md`.
3. **RH-14 closes.** The MLP does not meet sklearn's convergence tolerance, and it is also the least
   stable nonlinear model (spread 0.082 vs 0.021 for the forest) and does not win. The conclusion
   "the boosted tree wins in-distribution" therefore does not depend on hiding the warning.

## Optimisation (seed 11, 500 scenarios, both tiers)

| arm | tier C1 | tier C1+C2 | feasible? |
|---|---|---|---|
| **oracle** (true objective) | **513.92** | **513.76** | yes, both |
| equal-budget random search | 439.19 | 439.92 | yes |
| declared equal-thirds baseline (D6) | 313.70 | 313.70 | **no** (C-c and C-e) |
| surrogate: hist_gradient_boosting | 429.16 (promised 510.66) | 429.66 (promised 509.43) | yes |
| surrogate: random_forest | 420.17 (promised 496.74) | 421.16 (promised 517.43) | yes |
| surrogate: mlp | 343.99 (promised 524.19) | 360.74 (promised 584.13) | yes |
| surrogate: ridge | 212.08 (promised 312.17) | 25.23 (promised 430.17) | yes |
| surrogate: dummy | 314.21 | 17.99 | yes |

* **Section 12 control 3 passes:** the oracle beats the equal-budget random search in both tiers
  (513.9 vs 439.2; 513.8 vs 439.9), so the optimiser itself is not the thing that is broken.
* **The surrogate-exploitation metric is the headline.** Every **non-dummy** surrogate
  over-promises: the gap between what the model recommends and what the simulator returns at that
  recommendation runs +76.6 (forest, C1) to +404.9 (ridge, C1+C2). The dummy is the exception and is
  mis-calibrated in *both* directions; it promises 115.15 against a true 314.21 in tier C1
  (−199.1) and promises 115.15 against 17.99 in tier C1+C2 (+97.2). The best-calibrated surrogate is
  the boosted tree (+81.5 / +79.8), which is also the best in-distribution model, but even it claims
  510.7 and delivers 429.2.
* **A surrogate with no ranking ability returns an arbitrary feasible point.** The dummy arm in
  tier C1+C2 lands on a true yield of 17.99 while "promising" 115.15: with a constant prediction the
  objective is pure constraint penalty, so the solver stops wherever the violations vanish.
* **F5 FIRES on the oracle's own recommendation, in both tiers.** Only 26 % (C1) and 32 % (C1+C2) of
  ±5 % perturbations stay feasible, and the perturbation mean (505.4 / 504.9) sits below the
  recommended point (513.9 / 513.8). By the pre-declared rule the optimum is therefore reported as
  **artefactual**: it is pressed against the stability constraint (C-c), so a small change in the
  operating point pushes it out of the feasible set. **No "best recipe" is claimed**: that is the
  rule working as written, not a caveat added afterwards.
* **The declared baseline is infeasible on this simulator** (stress 1.000 > 0.35, pH_eff 6.20 < 6.5)
  at 313.70. The comparison uses the pre-declared feasible projection (365.8), and the oracle beats
  it by 40 %.

## Sensitivity of the ten pre-declared assumptions (sweep scale, seed 11, 250 scenarios)

Deltas against each assumption's own nominal level, so every number is like-for-like.

| assumption | level | median yield Δ | C1 recommendation Δ |
|---|---|---|---|
| ts_shape | monotone (CIT-0006's direction) | **−65.2 %** | **−32.1 %** |
| k_ref | 0.10 d⁻¹ | −34.3 % | −5.4 % |
| ts_shape | peak at 20 % | −24.8 % | −11.7 % |
| eta_lcfa | 0.030 | −24.1 % | −17.1 % |
| tan_half | 4.0 g/L | −23.1 % | −0.8 % |
| k_ref | 0.25 d⁻¹ | +22.3 % | +0.4 % |
| tan_half | 10.0 g/L | +16.8 % | −0.3 % |
| beta | 1.00 | +5.3 % | +5.3 % |
| pretreatment_response | 0.90 / 1.10 | −7.7 % / +9.8 % | **0.0 % / 0.0 %** |
| noise_scale | 0.5 / 2.0 | −2.1 % / +3.4 % | 0.0 % / 0.0 % |
| missingness | 0 % / 5 % | **0.0 %** | **0.0 %** |

Three readings:

1. **The recommendation is far more robust than the absolute level.** k_ref moves the median yield
   by a third while moving the recommended operating point by 5 %. Level and ranking respond
   differently, and the report should not conflate them.
2. **The two assumptions that change *which* region is best are the total-solids shape and the LCFA
   partition.** The monotone TS form, the contested direction (claim C-005, CIT-0006), costs 65 %
   of the median yield and moves the recommendation by a third. That single curve is the largest
   structural risk in the model, and it is exactly where the sources disagree.
3. **The pre-treatment response distribution moves the level but never the recommendation**
   (−7.7 % / +9.8 % on the median, 0.0 % on the recommended point): in this simulator the response factor
   multiplies everything uniformly, so it cannot change the ranking. That is also why the sweep
   cannot answer Q2 on its own, Q2 is answered by the data containing harmful, neutral and
   beneficial regimes, which the property tests check. And missingness changes
   nothing at all, exactly as designed: it changes which values are absent, not the values.

## Where the interpretation is written down

The contradictions this study ran into and the decisions they forced are in section 9 of `report.md`,
including the note that the F5 verdict depends on configuration (it fires in both tiers at this study
size, but at the smaller sweep size it fires on 22/30 C1 rows and 1/30 C1+C2 rows).

## What this directory does not contain

`report.md` (Phase 5), the twelve-section write-up, the plain-language explanation and the viva
questions. The report embeds the four figures that live here and presents the optimisation and
sensitivity results as labelled tables rather than as new figures: adding plotting code at the report
stage would have meant new untested modules after the coverage gate was met, and the tables carry
exactly the same numbers. Every table in the report is marked SIMULATED, as these files are.
