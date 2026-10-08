# Test-driven development log (Phase 3)

Append-only record of RED → GREEN → REFACTOR per change. Every claim below was observed by
running the command shown; nothing here is reconstructed from memory. Later waves (models,
evaluation, optimiser, end-to-end) append to this file rather than rewriting it.

Environment for every entry: Python 3.11.2, numpy 2.4.6, pandas 3.0.6, scikit-learn 1.9.1,
scipy 1.17.1, matplotlib 3.11.2, pytest 9.1.1, pytest-cov 7.1.0, hypothesis 6.168.5,
ruff 0.16.10, mypy 2.4.0 (installed with `python3 -m pip install --break-system-packages -r
requirements.txt pandas-stubs`; installs do not persist between sessions and are re-verified at
the start of each turn).

Standing commands:

```bash
python3 -m pytest -q --cov=src --cov-branch --cov-report=term-missing
python3 -m ruff check src tests
python3 -m mypy
python3 -m src.simulate_data --all-seeds --ood --outdir data/synthetic
```

---

## Wave 0: RED by construction (fixtures before implementation)

`tests/conftest.py` was written first, importing `src.simulate_data`, which did not exist.

- **RED evidence (observed):**

  ```
  $ python3 -m pytest tests/test_config.py tests/test_simulate_data.py tests/test_properties.py -x -q
  tests/test_simulate_data.py:16: in <module>
      from src import config
  E   ModuleNotFoundError: No module named 'src'
  1 error in 0.54s
  ```

- **GREEN:** `src/__init__.py`, `src/config.py`, `src/simulate_data.py` written against SPEC_V1.

## Wave A: simulator contract (4 test files, then the implementation)

| File | Purpose | Tests |
|---|---|---|
| `tests/test_config.py` | frozen constants, ranges, seeds, grids, labelling, leaf-module property | 15 |
| `tests/test_simulate_data.py` | determinism, schema, ranges, mass balance, surfaces, edge cases, regression pins | 40 |
| `tests/test_properties.py` | Hypothesis property tests (HYP-1…6) | 8 |
| `tests/test_spec_anchors.py` | every SPEC_V1 section 4.1 anchor re-derived from the frozen equations | 15 |
| `tests/test_ood_split_validation.py` | held-out family, split integrity, validation branches | 20 |
| `tests/test_cli.py` | CLI arguments, files written, error and guard paths | 9 |

First observed run of the new suite:

```
$ python3 -m pytest tests/ -q
11 failed, 34 passed, 16 errors in 1.19s
```

Failure classes, and what each one turned out to be (all fixed; none suppressed):

| # | Observed | Class | Cause | Fix / pin |
|---|---|---|---|---|
| B1 | `ValueError: operands could not be broadcast together with shapes (30,) (240,)` | **implementation bug** | the deterministic yield was computed per scenario but the noise was added per row | repeat the deterministic value to row level; `test_row_count_is_scenarios_times_replicates` |
| B2 | `KeyError: 'ph_setpoint'` in `test_constraints_are_inside_the_input_ranges` | **test bug** | the test assumed the setpoint lived in `INPUT_RANGES` | `SETPOINT_RANGE` exposed and registered in `INPUT_RANGES` |
| B3 | `assert ((0.45 + 0.05) + 0.05) > 1.0` | **test bug** | `c_hi, _ = ...` unpacked the *low* end | indexed `[1]` explicitly |
| B4 | `assert 'no BMP' in 'no bmp protocol is implemented…'` | **test bug** | case-sensitivity in the assertion, not a defect in the note | assertion rewritten to test the substance |
| B5 | `AssertionError: unexpected structural correlation 0.349 in ('ph_measured', 'olr_kg_vs_m3_d')` | **design defect in my own check** | the design-independence rule applies to *sampled decision variables*; `ph_measured` is computed inside the DGP and inherits loading dependence by construction | the rule was kept for design variables; a second mechanism (`config.DERIVED_CORRELATION_NOTES`, enforced by a test) now forbids *un-declared* derived correlations |
| B6 | `KeyError: 'simulated_methane_yield_ml_per_g_vs'` inside `validate_frame` | **implementation bug** | the mass-balance branch ran even when the target column was absent | branch now requires all three columns; `test_validate_handles_frames_without_the_target` |
| B7 | `test_ood_composition_sums_to_one` failed | **implementation bug** | clipping the derived protein fraction broke the simplex | sample protein and lipid, derive carbohydrate by rejection; validated by `test_ood_composition_sums_to_one` |
| B8 | `AssertionError: 28.069999999999997` (OOD mean, min 0.0) | **spec-vs-implementation conflict** | section 8's "other variables inside their normal ranges" sampled independently produces near-zero targets and exact zeros, which section 4.1 (iii) forbids | central bands for the non-extended axes; both variants recorded in `docs/known_issues.md` §4 |
| B9 | `KeyError: 'total_solids_pct'`-class `RUF046`/typing noise | tooling | redundant casts and narrow annotations | cleaned; see §Static analysis |

## Wave A: spec-level findings (these were **not** test failures)

| # | Finding | How it was caught | Action |
|---|---|---|---|
| S1 | an extra **inoculum factor** multiplied the yield, though section 3.3 contains no inoculum term and section 13.1 calls I:S a flat descriptor | re-deriving section 4.1's anchors by hand: the typical-mixed-food-waste anchor reproduces as 399.2 **only** without the factor (411.6 with it) | term and helper deleted; `test_inoculum_ratio_is_a_flat_descriptor` added |
| S2 | **extra rounding** had been applied to `hrt_days`, `inoculum_ratio`, `pretreatment_hours`, `pretreatment_temp_c` and the methane fraction, beyond the four columns section 3.6 lists | line-by-line comparison of the implementation against the frozen text | rounding restricted to the declared columns; `config.ROUNDING` documents the steps |

**Process lesson recorded, not hidden:** at the moment S1 was present the suite was **green**
(62 passed) even though the code contradicted the frozen specification. The check that caught it
was re-deriving the specification's own arithmetic, not a test. This is why
`tests/test_spec_anchors.py` now pins every anchor: a green suite only proves agreement with the
tests that exist.

## Wave A: REFACTOR

- `yield_endpoint` originally assigned its intermediates twice (an artefact of moving the
  pre-treatment helpers out); the dead first assignments were removed. Behaviour unchanged; the
  suite was re-run after the edit (same result).
- `_triangular_inverse` and the pre-treatment helpers were widened to accept scalars **and**
  arrays so that the specification's scalar anchor arithmetic and the vectorised generator share
  one implementation (no duplicated formula).

## Coverage (wave A, current totals are in the wave-B section at the end)

| Step | Result |
|---|---|
| after wave A first GREEN | `285 stmts / 1 miss, 54 branch / 1 partial` → 99 % |
| after adding the OOD, split and validation branches | 100 % |
| after adding the CLI guard test | 100 % statement, 100 % branch, 0 partial |

```
$ python3 -m pytest -q --cov=src --cov-branch --cov-report=term-missing
Name                   Stmts   Miss Branch BrPart  Cover   Missing
---------------------------------------------------------------
src/__init__.py            1      0      0      0   100%
src/config.py             76      0      0      0   100%
src/simulate_data.py     286      0     54      0   100%
---------------------------------------------------------------
TOTAL                    363      0     54      0   100%
Required test coverage of 100.0% reached. Total coverage: 100.00%
115 passed in 1.80s
```

- **Declared exclusion (exactly one):** `if __name__ == .__main__.:` (the module entry-point
  guard, which cannot run under an import-based runner). It is configured in `pyproject.toml`
  under `[tool.coverage.report] exclude_lines` with the reason stated inline. No other exclusion,
  no `# pragma: no cover` in `src/` (the two redundant pragmas written in waves A/B were removed in
  wave B so that the exclusion lives in exactly one declared place), and the `fail_under = 100`
  gate was never lowered.
- **Changed-line coverage:** the baseline for this branch is `main` at `4c3c9cf`, which contains
  no `src/` code at all. Every line in `src/` is therefore a changed line, and the measured 100 %
  statement + branch coverage *is* the changed-line coverage. Later phases will report the delta
  against this commit.
- Coverage is not evidence of correctness; it is evidence that no statement is untested. The
  correctness argument rests on the anchor tests, the property tests and the hand-mutation check.

## Property-based testing (Hypothesis, HYP-1…6)

`tests/test_properties.py` asserts properties that must hold for *any* honest implementation
(finiteness and bounds for arbitrary simplex points; monotone pre-treatment progress; bounded,
decreasing inhibition; determinism of the surface independent of the sampler). Settings:
`max_examples` 50–150 per property, `deadline=None` (the assertion is the target, not latency).
Run: `python3 -m pytest tests/test_properties.py -q` → passed.

## Mutation testing status (wave A, wave-B mutants are listed at the end)

Tool-based mutation testing was **not run** (no mutation tool is installed in this environment,
and installing one was not part of the approved dependency set). Instead, four mutants were
inserted by hand into the frozen constants and the suite was re-run; all four were killed:

| Mutant | Failures | Example killer |
|---|---:|---|
| `PH_DECAY` 0.7 → 0.8 | 5 | `test_spec_anchors.py::test_divergent_anchor_values_are_pinned` |
| `VS_TS` 0.85 → 0.90 | 16 | `test_yield_reference_configuration_matches_the_frozen_anchor` |
| `C_TAN_HALF` 6.0 → 5.0 | 16 | `test_yield_reference_configuration_matches_the_frozen_anchor` |
| `washout` denominator + 1 | 1 | `test_washout_collapses_below_the_threshold` |

The source was restored after each mutation and the restoring state was verified by re-running the
suite (115 passed) and by reading the constants back (`PH_DECAY 0.7 | VS_TS 0.85 | C_TAN_HALF 6.0`,
`washout(5, 9, 12) = [0.0, 0.5, 1.0]`). Weak spots the mutation check exposes: one mutant
(`washout`) was caught by a single test, i.e. that behaviour is thinly pinned.

## Static analysis (wave A; wave-B re-run in the wave-B section)

| Tool | First run | Final |
|---|---|---|
| ruff (`E,F,W,I,B,UP,SIM,PTH,NPY,RUF`) | 16 errors (ambiguous `l`, redundant casts, tuple concatenation, one accidental double negative in a test) | `All checks passed!` |
| mypy (`disallow_untyped_defs` on `src` **and** `tests`) | 24 errors (missing annotations, pandas stubs, ndarray-vs-float parameters) | `Success: no issues found in 10 source files` |

`pandas-stubs` is installed explicitly (and listed in the workflow) rather than adding a blanket
`ignore_missing_imports` for pandas: real types, not a silenced check.

## Test inventory mapped to the required categories

| Required category | Where |
|---|---|
| deterministic generation, seed sensitivity | `test_simulate_data.py` (determinism block) |
| mixture bounds / sum-to-one | `test_composition_sums_to_one`, `test_ood_composition_sums_to_one` |
| NaN / inf / wrong-type / empty inputs | `test_validate_frame_*`, `test_wrong_type_*`, `test_validate_frame_rejects_empty_and_wrong_types` |
| ranges, non-negativity, mass balance | range block + `test_mass_balance_between_outputs` |
| schema / dtypes / serialisation | schema block, `test_csv_round_trip`, `test_written_csv_is_reloadable_and_labelled` |
| scenario separation, train-only preprocessing | `test_simulate_data.py` split block; `test_preprocess_leakage.py` (group overlap, near-duplicate guard, train-only imputer/scaler statistics, leakage guard per column class) |
| tiny / constant / singular cases | `test_tiny_dataset_is_supported`, `test_inoculum_ratio_is_a_flat_descriptor` (a constant feature) |
| all five models fit/predict/save-load | `test_train_models.py` (model-set, estimator-type, fit/predict, save/load, metadata) |
| hand-computed metrics incl. undefined R² | `test_regression_metrics_*` (RMSE `sqrt(4/3)`, R² `-1`, undefined R² → `None`) |
| optimiser constraints, infeasibility, boundary optima, reproducibility | **pending** (wave D) |
| CLI errors + small end-to-end run | `test_cli.py` (7 error/guard paths) + `test_train_cli_*` (fit-and-write, duplicate warning, unknown model); full pipeline run arrives with `evaluate.py` |
| property-based | `test_properties.py` |
| static checks | ruff + mypy above |
| regression test per bug | B1, B6, B7, S1, S2, B5 pins are named above |

## Not yet done (honest status)

- `src/train_models.py` now exists (wave B, below). `src/evaluate.py`, `src/optimize.py` and the
  end-to-end integration test do not exist yet; the Phase 3 build is unfinished and this log is
  appended to, never rewritten.
- The GitHub Actions workflow is committed and was **first executed on 2026-10-08**, when it failed on a
  bare `pytest` that could not import `src` and on a `mypy` error that appears only with the numpy 2.5
  stubs on Python 3.12. Both fixes are in the tree; `docs/notebook.md` records the runs.
- Figure/plot tests (`matplotlib`) are not written; the plotting code arrives with `evaluate.py`.

## Wave A: end-to-end smoke run of the generator

```
$ python3 -m src.simulate_data --all-seeds --ood --outdir /tmp/smoke
seed 11: wrote /tmp/smoke/foodwaste_biogas_seed11.csv (4000 rows, 500 scenarios) [SIMULATED]
seed 11: wrote /tmp/smoke/foodwaste_biogas_ood_seed11.csv (480 rows, held-out OOD outside the training envelope) [SIMULATED]
… (seeds 23, 37, 41, 59)
```

Observed facts from the written files: 4 000 rows and 31 columns per seed; split by scenario
350 train / 75 validation / 75 test (= 70 / 15 / 15 %); every row `data_provenance = synthetic`,
`simulator_version = SPEC_V1`; the five-seed set including held-out families occupies 9.6 MB. The
files were written to a temporary directory, not into `data/synthetic/`, Phase 4 owns the committed
dataset, and the size rule recorded in `.gitignore` (10 MB) is satisfied by the measurement above.

## Wave B: splitting, leakage guards and the five models

Two test files were written **before** any implementation code:

```
$ python3 -m pytest tests/test_preprocess_leakage.py -q
ModuleNotFoundError: No module named 'src.train_models'
7 failed, 19 errors in 1.1s
```

That is the strongest available form of RED: the contract (`split_frame`, `make_feature_frame`,
`fit_preprocessor`, `build_model`, `regression_metrics`, `fit_model`, `save_model`, `load_model`)
did not exist, so nothing about training could pass. `tests/test_train_models.py` was added in the
same state and failed for the same reason.

### Defects the tests found while the implementation was being written

| # | Symptom | Root cause | Fix (code) or correction (test) |
|---|---|---|---|
| B8 | `NotFittedError` in 17 tests | `fit_preprocessor` returned a `ColumnTransformer` that was built but never fitted | replaced by an explicit `FeaturePreprocessor` dataclass holding a **fitted** `SimpleImputer` and `StandardScaler`, both inspectable |
| B9 | non-finite values reaching the scaler, duplicated columns | the `ColumnTransformer` imputed *and* scaled over the same column list, so the output had twice as many columns as declared | one frozen feature list, impute → scale as two ordered steps; a test asserts the transformed width equals `len(config.FEATURES)` |
| B10 | `ValueError: data must be finite` from `cKDTree` | `ph_measured` is missing in 2 % of rows, so the duplicate guard met NaN | NaN sentinel `-999` before distances (the guard only ever compares feature vectors; the sentinel is the same value the imputer would otherwise have to invent) |
| B11 | two hand-written expectations failed against correct code | my arithmetic: RMSE is `sqrt(4/3)` not `sqrt(2/3)`; R² is `-1` not `0` when SS_res = 4 and SS_tot = 2 | tests corrected; `regression_metrics` was **not** changed |
| B12 | the leakage mutation test passed even with train statistics replaced by full-data statistics | at 60 scenarios the train median and the full-data median coincided, so the test had no power | added the `splits_large` fixture (250 scenarios), where the test carries a documented power assertion |
| B13 | the permuted-target control read +0.066 R² for Ridge, above its own 0.05 gate | one permutation is a single noisy draw, not a control | the control now reports mean/min/max over **5** permutations; the gate applies to the mean and the max is reported alongside |
| B14 | `ConvergenceWarning` from the MLP | sklearn's tolerance is not met at the iteration cap | cap raised 600 → 2000; **it still warns**, so the warning count is now stored in the model artifact and its JSON sidecar instead of being filtered |

The MLP warning is deliberately not suppressed. A hand measurement (250 scenarios: `max_iter=2000`
→ validation R² 0.63; `max_iter=5000` → 0.56, still "not converged") is recorded as a comment next
to the estimator: more iterations did not buy accuracy here, so the caveat is reported, not hidden.

### Mutation testing (wave B, hand-inserted)

| Mutant | Failures | Verdict |
|---|---:|---|
| impute `median` → `mean` | 1 | killed |
| `StandardScaler` → `with_mean=False` | 17 failed / 8 errors | killed |
| duplicate guard `len(names) > 1` → `> 2` | 1 | killed |
| selection by **training** R² instead of validation R² | **0** | **survived the first pass** |
| (restore) unmutated source, full re-run || 171 passed, 100 % coverage |

The survivor is the important result: `tune_model` was documented as "select on validation" but no
test could tell the two rules apart, because on every fixture the two rules happened to agree. The
fix is `test_selection_uses_validation_not_training_score`, which (a) verifies on the fixture that
the training-argmax and validation-argmax configurations **differ**, so the assertion cannot become
vacuous, and (b) checks the selected parameters equal the validation-argmax. With that test the
mutant is killed (1 failure) and the suite is green again without it. A recording bug in the other
direction was also closed: the persisted tuning log records `train_r2` for information only, and
`test_test_split_is_never_used_for_selection` asserts the word "test" never appears in it.

### Wave-B totals

```
$ python3 -m ruff check src tests          → All checks passed!
$ python3 -m mypy                          → Success: no issues found in 13 source files
$ python3 -m pytest -q --cov=src --cov-branch --cov-report=term-missing
Name                   Stmts   Miss Branch BrPart  Cover   Missing
src/__init__.py            1      0      0      0   100%
src/config.py             76      0      0      0   100%
src/simulate_data.py     286      0     54      0   100%
src/train_models.py      232      0     72      0   100%
TOTAL                    595      0    126      0   100%
Required test coverage of 100.0% reached. Total coverage: 100.00%
171 passed, 8 warnings in 63.00s
```

Static-analysis change in wave B: `scikit-learn-stubs` was installed so scikit-learn is checked
with real types instead of being silenced; `joblib` and `scipy` ship no types in the pinned
versions, and only those two modules carry a documented `ignore_missing_imports` override in
`pyproject.toml` (no global silencing, no `# type: ignore` in `src/`).

Honest status: the 8 warnings in the full run are the MLP convergence notices plus the
permuted-target control's fitted-but-unconverged MLP; both are recorded in the artifact metadata,
and no `filterwarnings` rule suppresses them (the single configured entry **escalates**
`RuntimeWarning` to an error, which is how a silent `log(0)` would be caught). `src/evaluate.py`, `src/optimize.py` and the
end-to-end integration test are still missing, so Phase 3 is unfinished.

## Wave C: the five-seed evaluation pipeline

`tests/test_evaluate.py` (40 tests) was written and run before `src/evaluate.py` existed:

```
$ python3 -m pytest tests/test_evaluate.py -q
ModuleNotFoundError: No module named 'src.evaluate'
18 failed, 14 errors in 0.52s
```

### Defects and corrections on the way to GREEN

| # | Symptom | Root cause | Fix |
|---|---|---|---|
| C1 | `test_summary_is_deterministically_ordered` failed on the first GREEN run | the summary depended on **row order**: float addition is not associative, so `mean` over a reversed row list differed in the last bits | the values inside each summary cell are sorted before `mean`/`std`; a summary that changes when the input is shuffled is a reproducibility bug, not a rounding detail |
| C2 | `test_f7_fires_when_the_best_model_overlaps_the_dummy_baseline` could never fire | my first fixture gave the *best-mean* model the narrowest range, so the rule was unsatisfiable by construction | fixture rebuilt: the best model by mean owns one bad seed, so its min–max range reaches into the baseline band, the situation F7 exists to catch |
| C3 | mypy: `permutation_importance` returns `Bunch | dict` under the stubs | attribute access is not guaranteed on the union | item access plus `np.asarray(..., dtype=float)`; the values, not the access style, are what the table reports |
| C4 | ruff: 5 findings (unused `noqa`, unused unpacked variable, redundant `int()` cast, unused import, import order) || fixed; the tie-break in `evaluate_decision_rules` is now an explicit `sorted(...)[-1][1]` so it is deterministic *and* used |

### Recorded interpretation (not a threshold change)

SPEC_V1 §9.1 phrases F7 as "the mean ± spread of the best model overlaps the dummy baseline's
spread". Implemented reading: **the observed min–max range of each**, which is the *wider* interval
and therefore the more conservative rule; it fires the warning more readily than a ±1 standard
deviation band would. The choice is stated in the rule string that is written into
`results/decision_rules.json`, so the report cannot silently pick the other reading later.

### Mutation testing (wave C, hand-inserted)

| Mutant | Failures | Killer test |
|---|---:|---|
| `F3_THRESHOLD` 0.95 → 0.50 | 2 | `test_f3_does_not_fire_when_ridge_lags_the_trees`, `test_rules_record_their_own_thresholds` |
| F7 overlap `and` → `or` | 1 | `test_f7_does_not_fire_when_the_ranges_are_disjoint` |
| summary `std` `ddof=1` → `0` | 1 | `test_summary_is_hand_checkable` |
| `figure_seed` first → last seed | 1 | `test_figures_describe_one_named_seed_and_the_tables_cover_all_of_them` |

Four mutants, four killed, source restored and re-verified (`40 passed`). Tool-based mutation
testing is still **NOT RUN** (no mutation tooling in the approved dependency set).

### Wave-C totals

```
$ python3 -m ruff check src tests          → All checks passed!
$ python3 -m mypy                          → Success: no issues found in 15 source files
$ python3 -m pytest -q --cov=src --cov-branch --cov-report=term-missing
Name                   Stmts   Miss Branch BrPart  Cover   Missing
src/__init__.py            1      0      0      0   100%
src/config.py             76      0      0      0   100%
src/evaluate.py          246      0     64      0   100%
src/simulate_data.py     286      0     54      0   100%
src/train_models.py      232      0     72      0   100%
TOTAL                    841      0    190      0   100%
Required test coverage of 100.0% reached. Total coverage: 100.00%
211 passed, 15 warnings in 108.00s (0:01:48)
```

The 15 warnings are MLP convergence notices (every evaluation run fits five models over several
seeds, and the MLP never meets sklearn's tolerance). They are counted into each model artifact's
`convergence_warnings` field; nothing is filtered.

### Smoke run of the new pipeline (NOT the study result)

```
$ python3 -m src.evaluate --seeds 11,23 --n-scenarios 60 --ood-scenarios 12 --outdir /tmp/eval_smoke
seed 23 dummy: test R2=-0.4369 MAE=129.34 RMSE=146.41 [SIMULATED]
seed 23 ridge: test R2=+0.3169 MAE=81.21 RMSE=100.95 [SIMULATED]
seed 23 random_forest: test R2=+0.6957 MAE=53.17 RMSE=67.38 [SIMULATED]
seed 23 hist_gradient_boosting: test R2=+0.7195 MAE=45.28 RMSE=64.68 [SIMULATED]
seed 23 mlp: test R2=+0.1797 MAE=91.46 RMSE=110.62 [SIMULATED]
… (two-seed means: dummy -0.2291 ± 0.2939, ridge +0.2987 ± 0.0257, random_forest +0.4846 ± 0.2986,
   hist_gradient_boosting +0.5629 ± 0.2215, mlp +0.3326 ± 0.2163)
F3: informative - the nonlinear models earn their place | F7: stable [SIMULATED]
wrote 10 artefacts to /tmp/eval_smoke [SIMULATED]
```

10 artefacts, 460 KB, ~90 s. This is a **two-seed, 60-scenario smoke test** used to prove the
wiring works; it is not the study result, it is not five seeds, and no conclusion may be drawn from
it. It does, however, produce the first signal relevant to RH-14: at this size the MLP is both weak
(0.18 on seed 23) and unstable, while the gradient booster leads. Phase 4 decides with five seeds.

## Wave D: the constrained optimiser and its robustness harness

`tests/test_optimize.py` (62 tests) was written and run before `src/optimize.py` existed:

```
$ python3 -m pytest tests/test_optimize.py -q
ModuleNotFoundError: No module named 'src.optimize'
34 failed, 15 errors in 0.48s
```

### Defects the tests found while the implementation was being written

| # | Symptom | Root cause | Fix (code) or correction (test) |
|---|---|---|---|
| D1 | the solver returned the **worst** feasible point (x = 5.0 for an objective peaking at 2.0) | `differential_evolution` minimises; the `maximize=True` keyword does not exist in the pinned SciPy | objective negated explicitly, sign restored, commented as a place where a slip would look like a result |
| D2 | `RuntimeError: The map-like callable must be of the form f(func, iterable)` | the batched (`vectorized=True`) objective path is incompatible with `polish=True` in the pinned SciPy | batched objectives replaced by scalar candidate-dict objectives with the array maths inside; the dual-shape branch disappeared rather than being exercised by a synthetic test |
| D3 | `UserWarning: 'vectorized' has overridden updating='immediate'` | contradictory solver arguments | argument dropped |
| D4 | `KeyError: 'ph_setpoint'` | `dict.get(key, other[key])` evaluates its default **eagerly**, so the fallback raised even when the key it was looking for was present | explicit conditional, with the reason in a comment |
| D5 | `RuntimeWarning: Mean of empty slice` escalated to an error on a corner candidate | an infeasible candidate can have **zero** feasible perturbed draws, and `np.mean([])` is a warning-then-nan | `mean/min/max` are `None` in that case and F5 reports `below_reference: None` ("not evaluable"), never a fabricated number |
| D6 | `UnboundLocalError: baseline_ph` | my own line-wrapping edit moved an assignment inside an `if` | fixed; seven tests failed on it, which is what the suite is for |
| D7 | my "feasible" test point for the penalty check was **infeasible by 0.0033** in C-c | at OLR 2.5 that mixture sits exactly on the stress threshold | test point moved to OLR 1.5; `constraint_report` was not changed |

### Findings about the frozen specification (recorded, not repaired)

1. **The declared baseline (decision D6) violates two frozen constraints.** Equal thirds at
   mid-range settings gives `VFA_stress = 1.000` (limit 0.35) and `pH_eff = 6.20` (limit 6.5), so
   the SPEC §10 "baseline arm" is **infeasible** on this simulator, at a true yield of 313.7.
   Neither the mixture nor the thresholds were edited: the declared point is reported exactly as
   specified, *and* a pre-declared companion - the closest feasible mixture at the same process
   settings, found on a deterministic 0.002-resolution grid, `c = 0.672, p = 0.250, l = 0.078`,
   yield 365.8 - is used for the F5 comparison and the oracle sanity check. "Beats an infeasible
   baseline" would not have been evidence of anything.
2. **The feasible box is small.** Measured with this module's own constraint logic on 200 000
   uniform draws over the declared ranges: **12.34 %** of the box satisfies all six constraints.
   C-c (stability) and C-e (realised pH) do the cutting, the same two constraints that make the
   declared baseline infeasible. This is a property of the frozen thresholds and the frozen
   stress model, and it is the reason the F5 knife-edge condition exists.
3. **A documentation inconsistency inside SPEC_V1.** §3.1's table gives `lipid_fraction`
   0.02–0.30, while §6's frozen sampler (S-6) draws `l ~ Tri(0.05, 0.30, 0.15)` and
   `config.INPUT_RANGES` carries 0.05. The operational reading is used (0.05) because the
   simulator that generates the data implements the sampler; the discrepancy is recorded rather
   than silently resolved in either direction. SPEC_V1 stays frozen.
4. **The inoculum ratio is held fixed, not optimised.** SPEC §10 lists it among the decision
   variables, but §13.1 gives it no term in the yield equation (RH-13), so a solver would fill it
   with an arbitrary number that a "best recipe" table would then present as chosen. It is held at
   the baseline value and `test_inoculum_flatness_is_verified_not_assumed` checks the flatness
   over its whole range rather than trusting the specification.

### Mutation testing (wave D, hand-inserted)

| Mutant | Failures | Verdict |
|---|---:|---|
| penalty `10 000` → `0.0` | 4 failed, 12 errors | killed |
| F5 knife-edge threshold `0.5` → `0.0` | 3 | killed |
| drop the derived-lipid check from the box constraint | 2 | killed |
| `assert_feasible` never raises | 1 | killed **only by one test** → the enforcement path was then pinned a second time by `test_the_run_refuses_to_return_an_infeasible_recommendation`, which monkeypatches the solver to hand back an infeasible point |
| sign slip on the restored solver value | 4 | killed |
| perturbation shifts **not** scaled by each variable's range width | **0 (survived)** | **survived**: "±5 % of range width" was unpinned: every other perturbation assertion holds for a ball of any size. `test_the_perturbation_scale_is_a_fraction_of_each_variable_s_range_width` now pins the observed spread per variable against `2 × fraction × (high - low)` with a 15 % tolerance; the mutant is killed (1 failure) |
| (my own error) a mutant written as `* 1.0`, i.e. a no-op | 0 | **not a valid mutant**: recorded because the first attempt produced a meaningless "survival" |

Seven mutants attempted; five killed, one invalid by my own construction, one genuinely survived
and is now killed by a new test. Tool-based mutation testing remains **NOT RUN**.

### Wave-D totals

```
$ python3 -m ruff check src tests          → All checks passed!
$ python3 -m mypy                          → Success: no issues found in 17 source files
$ python3 -m pytest -q --cov=src --cov-branch --cov-report=term-missing
src/__init__.py            1      0      0      0   100%
src/config.py             76      0      0      0   100%
src/evaluate.py          248      0     64      0   100%
src/optimize.py          393      0    102      0   100%
src/simulate_data.py     286      0     54      0   100%
src/train_models.py      232      0     72      0   100%
TOTAL                   1236      0    292      0   100%
Required test coverage of 100.0% reached. Total coverage: 100.00%
273 passed, 15 warnings in 137.35s (0:02:17)
```

The 11 uncovered lines and 11 partial branches found at the first wave-D coverage run were all
error paths, and every one was closed by a test (guards for missing variables, wrong vector
lengths, degenerate solver budgets, zero random-search draws, an all-infeasible draw set, an
impossible baseline projection, a degenerate perturbation fraction, empty model/tier lists).
None was waived.

### Smoke run of the optimiser (NOT the study result)

```
$ python3 -m src.optimize --seed 11 --n-scenarios 60 --models dummy,ridge,hist_gradient_boosting \
    --perturbation-draws 80 --max-iterations 30 --population-size 10 --outdir /tmp/opt_smoke2
tier C1 - achievable at home (tier C1) [SIMULATED]
  oracle: true yield 512.40 (feasible=True) [SIMULATED]
  random_search: true yield 412.08 (feasible=True) [SIMULATED]
  baseline (declared D6): true yield 313.70 (feasible=False) [SIMULATED]
  surrogate dummy: predicted 123.34 -> true 325.12 (gap -201.78) [SIMULATED]
  surrogate ridge: predicted 365.88 -> true 191.26 (gap +174.63) [SIMULATED]
  surrogate hist_gradient_boosting: predicted 369.31 -> true 398.16 (gap -28.84) [SIMULATED]
  perturbation +/-5%: mean 502.63, feasible 25% of draws; F5: artefactual [SIMULATED]
tier C1+C2 - laboratory recommendation (tiers C1 + C2) [SIMULATED]
  oracle: true yield 514.26 (feasible=True) [SIMULATED]
  random_search: true yield 386.46 (feasible=True) [SIMULATED]
  baseline (declared D6): true yield 313.70 (feasible=False) [SIMULATED]
  surrogate dummy: predicted 123.34 -> true 389.07 (gap -265.74) [SIMULATED]
  surrogate ridge: predicted 510.79 -> true 14.30 (gap +496.49) [SIMULATED]
  surrogate hist_gradient_boosting: predicted 399.87 -> true 416.41 (gap -16.54) [SIMULATED]
  perturbation +/-5%: mean 503.46, feasible 26% of draws; F5: artefactual [SIMULATED]
```

Three things this smoke shows about **the machinery** (one seed, 60 scenarios, three models - none
of it is a study result): the oracle beats the equal-budget random search in both tiers (SPEC §12
control 3 passes), the surrogate arm behaves exactly as the exploitation warning predicts (Ridge
promises 510.8 and the simulator returns 14.3; the gradient booster is much better calibrated), and
F5 fires on the **oracle's own** recommendation because only a quarter of ±5 % perturbations stay
feasible - the optimum is pressed against the stability constraint. Phase 4 decides with five seeds
and the full model set.

## Wave G: the pre-declared sensitivity sweep (SPEC_V1 §11)

`tests/test_sensitivity.py` (42 tests) was written and run before `src/sensitivity.py` existed and
before the simulator had its sweep hooks:

```
$ python3 -m pytest tests/test_sensitivity.py -q
36 failed, 4 errors in 0.86s
```

### What had to be added to the simulator, and why that is safe

Three hooks, each with a default that reproduces the frozen behaviour **exactly**:
`config.RESPONSE_CENTRE` (the sampler used a literal `1.0`), `config.NOISE_SCALE` (multiplier on
both noise sigmas) and `config.TS_SHAPE` with a declared second form. Two tests exist for the
safety of that claim rather than the hope of it: `test_a_nominal_sweep_level_reproduces_the_frozen_dataset`
compares the generated frame byte for byte under every nominal level, and
`tests/test_integration_e2e.py::test_the_committed_dataset_is_what_the_generator_produces_today`
still re-derives all five committed seeds.

The override mechanism is a context manager that patches `src.config` attributes and restores them
in a `finally`. That is deliberate global mutable state, so three tests constrain it: restoration
after a normal exit, restoration after a raise, restoration after nesting, plus a refusal list so a
typo cannot patch an unrelated constant.

### Defects and corrections

| # | Symptom | Root cause | Fix |
|---|---|---|---|
| G1 | `TypeError: _level() missing 1 required positional argument` | my code-generation pass rewrote `_level` to take a display label *and* a numeric value but did not update the 29 call sites | call sites regenerated; the grid is now checked by `test_every_level_matches_the_frozen_specification`, which compares each `value` against the numbers written in SPEC §11 |
| G2 | the sweep was not reproducible | rows carried `runtime_s`, so two identical runs differed by wall-clock time | the per-row timer was removed; a result row must be result-bearing, and the total runtime lives in the metadata |
| G3 | `test_the_sweep_rejects_*` raised `TypeError` instead of `ValueError` | `run_sensitivity_sweep` and `sweep_level` had required solver arguments, so guard paths could not be reached without running a full sweep | defaults added (20 / 8 / 20), matching the CLI defaults |
| G4 | `assert 'spec' in 'SPEC_V1 11 row 1'` | my test compared a lowercase substring against an uppercase source string | comparison lowercased |
| G5 | `KeyError: 'median_delta_pct'` | my test used a column name that does not exist; the produced names mirror the value columns (`median_yield_delta_pct`, `c1_yield_delta_pct`, `c1_c2_yield_delta_pct`) | test corrected; the three delta columns are now named in this log so the next reader does not guess |
| G6 | `test_the_noise_scale_hook_...` failed at a 2 % tolerance | the reported number is a **mixture** median over scenarios with different deterministic means, so widening each component's log-normal spread moves the mixture's quantiles by ~3.7 % even though no component's median moves | tolerance stated at 10 % **with the reason in the test**, rather than tightened to fit |
| G7 | the missingness assumption had no nominal level | SPEC §11 row 10 prints one rate (2 %), while the frozen simulator carries two (2 % pH, 1.5 % temperature) | the nominal level keeps the simulator's pair so a delta of exactly zero is measurable, and the wording gap is recorded in the assumption note, in the metadata and here |
| G8 | the wave-G mutation table in this log carried **failure counts that had never been observed** (23 / 1 / 1 / 4) | I wrote the table from what the mutants *should* break instead of from the run output, the exact failure mode this log exists to catch | mutants re-applied one at a time and re-measured (below); every count in the table is now an observed line, and this defect is recorded rather than silently corrected. Same class of error is checked once more in the Phase-4 block (`over-promises`) |

### Mutation testing (wave G, hand-inserted)

Each mutant was applied to `src/sensitivity.py` in place, `tests/test_sensitivity.py` re-run
(46–56 s per mutant), then the file restored from a copy and the suite re-verified green
(`42 passed in 55.01s`). Observed lines:

| Mutant | Observed | Killed by (example) | Verdict |
|---|---|---|---|
| `constant_override` restores nothing (drop the `finally`) | 5 failed, 37 passed | `test_the_override_context_patches_and_restores`, `test_the_override_context_restores_after_nesting` | killed |
| `is_nominal` computed as `False` everywhere | 2 failed, 36 passed, 4 errors | `test_the_sweep_is_reproducible`, `test_the_cli_writes_the_sweep_artefacts` | killed |
| the delta divides by the *first* row instead of the nominal row | 2 failed, 40 passed | `test_the_sweep_reports_a_delta_against_the_nominal_level_of_the_same_assumption`, `test_an_assumption_without_a_nominal_level_is_refused` | killed |
| `_resolve` accepts any level string | 5 failed, 33 passed, 4 errors | `test_sweeping_one_level_reports_yield_and_recommendation`, `test_sweeping_rejects_an_unknown_assumption_or_level` | killed |

Four mutants, four killed. Tool-based mutation testing remains **NOT RUN**.

### Wave-G totals

```
$ python3 -m ruff check src tests          → All checks passed!
$ python3 -m mypy                          → Success: no issues found in 21 source files
$ python3 -m pytest -q --cov=src --cov-branch --cov-report=term-missing
src/sensitivity.py       139      0     40      0   100%
TOTAL                   1389      0    336      0   100%
341 passed, 1 skipped, 15 warnings in 286.69s
```

## Phase 4: execution at study size

Three commands, in order, with their runtimes on the 2-vCPU sandbox. All outputs are in `results/`
and are catalogued in `results/README.md`; the analysis, not the raw numbers, is what follows.

**1. Evaluation, five seeds × 500 scenarios (2m31s).** The numbers are **identical** to the Phase-3
probe run into `/tmp` before this phase began, 0.4540 / 0.7785 / 0.8124 / 0.6947 and a dummy at
−0.0322, which is the determinism claim being tested by the study run rather than asserted.
F3 does not fire (informative); F7 does not fire (stable).

**2. Optimiser, both tiers, five models, 500 scenarios (3m41s).** Oracle 513.92 / 513.76, beats the
equal-budget random search (439.19 / 439.92, SPEC §12 control 3 passes). Every **non-dummy**
surrogate over-promises, gaps +76.6 (forest, C1) to +404.9 (ridge, C1+C2); the dummy is the
exception and mis-calibrates in both directions (−199.1 C1, +97.2 C1+C2), which is the honest
statement of a claim I first wrote as "every surrogate over-promises" without checking the sign.
**F5 fires on the oracle in both tiers** because only 26 % / 32 % of ±5 % perturbations remain
feasible, so by the pre-declared rule the optimum is reported as artefactual and no best recipe is
claimed.

**3. Sensitivity sweep, ten assumptions × three levels (8m49s).** Largest median-yield effects:
TS shape monotone −65.2 %, k_ref 0.10 −34.3 %, TS peak-at-20 % −24.8 %, eta 0.030 −24.1 %. Largest
recommendation effects: TS monotone −32.1 %, eta 0.030 −17.1 %. Two assumptions move the level but
**not** the recommendation at all, the pre-treatment response distribution (−7.7 % / +9.8 % on the
median, 0.0 % on the recommendation, because the factor acts on the latent response and is uniform
over mixtures) and missingness (exactly 0.0 %, as designed).

### One defect found by the guard once `results/` existed

`results/decision_rules.json` was written without a provenance header, the only artefact in the
directory that a reader could not date or attribute. The content guard written in wave F caught it
on its first real run over `results/`. Fixed in `src/evaluate.py`, re-run at study size, and pinned
by `test_the_decision_rules_artefact_carries_provenance` (P4-1). This is the guard paying for
itself, which was the argument for writing it before the results existed rather than after.

### P4-2: a catalogue number written from memory instead of measured

Six documents, plus this log's own Phase-4 summary and the commit message, described `results/` as
"17 files, 632 KiB". Measured at the close:

```
$ python3 -c "import pathlib; fs=[p for p in pathlib.Path('results').rglob('*') if p.is_file()];
              print(len(fs), sum(p.stat().st_size for p in fs))"
16 624651          # 16 files, 624 651 bytes = 610.0 KiB
```

The count was wrong by one file and the size by 22 KiB. This is defect **G8's class** appearing a
third time (the first was the unobserved mutation counts, the second the "every surrogate
over-promises" phrase): an assertion about the artefact that felt known. Corrected everywhere by
measurement, and recorded here because a size claim that drifts is how a catalogue becomes decorative.
No test can pin prose, so the fix is procedural: the numbers in a catalogue line are copied from a
command, not from working memory, the same rule the arithmetic in the metrics tests follows.

### Phase 4's remaining artefacts

**The conflict map.** `docs/contradictions.md` closes the `G-P-4` row (contradiction →
`claim_id` links) and with it the `G-L8` gate, so the M-decisions the Phase-2 disagreement map
deliberately left open are settled on measured evidence rather than argument: M-1 (tier separation, 
closed; the tier does not raise what is achievable; it widens the surrogates' room to over-promise),
M-2 (costs stay out of the objective, closed as declared), M-3 (informative about the simulator's
structure, not about recommending, closed, two-sided), M-4 (collinearity criticism retained, with
`ph_measured` first in every model as the reason), M-5 (Stage 1 stays; its factor moves the level but
0.0 % of the recommendation). M-6 is carried to Phase 5 by the map's own rule. A1 of that map, the
contested TS direction, `C-005`, is the largest structural risk the sweep found (−65.2 % median).

**The CLI chain test now covers five CLIs.** `tests/test_integration_e2e.py` chained simulate →
train → evaluate → optimise; the sensitivity CLI arrived in wave G and was covered only by its own
file. The chain test is renamed `test_the_five_clis_chain_into_one_pipeline` and runs the sweep CLI
at minimum settings as its last step. This is a test-only change: no production line changed, so
there is no RED to show, the test was observed green on its first run, and that is recorded instead
of inventing a RED.

**A preregistered deliverable that was not built.** `docs/preregistration.md` §14 promised
`CLI (python -m src.pipeline …)` for group D-CLI-01..05. What exists is five separate CLIs, each with
its own parser and tests, chained by the integration test above. The brief's file list never named a
`pipeline` module, and a wrapper would add an entry point without adding science. It is recorded here
as a **declared deviation** rather than renamed into existence; if a single-command entry point is
wanted, Phase 5 can add it, and it would be tested like any other CLI.

### The Phase-4 gate, re-run after the final touch-ups

The 341-pass figure above predates two changes made after it (one test: the empty-model-list guard in
`constant_override`; one src line: explicit record-key conversion). The full gate was therefore re-run
at the Phase-4 close rather than inherited:

```
$ python3 -m ruff check src tests          → All checks passed!
$ python3 -m mypy                          → Success: no issues found in 21 source files
$ python3 -m pytest -q --cov=src --cov-branch --cov-report=term-missing
src/sensitivity.py       138      0     40      0   100%
TOTAL                   1388      0    336      0   100%
342 passed, 1 skipped, 15 warnings in 288.51s (0:04:48)
# Phase-5 close: the one skip was `report.md`; with the report written the final
# re-run reads 343 passed, 0 skipped in 313.99s (0:05:13)
```

342 rather than 341 because the P4-1 regression test (`test_the_decision_rules_artefact_carries_provenance`)
was added after the earlier run; the CLI-chain test was renamed and extended (four → five CLIs) rather
than duplicated, so it is the same single test. The one skip is `report.md`, which Phase 5 writes.

## P5-1: the dataset's byte size had been wrong since Phase 3 (found at the Phase-5 close)

The figure "10 003 242 bytes (9.5 MiB)" for `data/synthetic/` appears in six documents written between
Phase 3 and Phase 4. Measured at the Phase-5 close:

```
$ python3 -c "import pathlib; fs=[p for p in pathlib.Path('data/synthetic').rglob('*') if p.is_file()];
              print(len(fs), sum(p.stat().st_size for p in fs))"
21 9999347
$ git ls-tree -r -l HEAD data/synthetic | awk '{s+=$4; n++} END {print n, s}'
21 9999347
```

The **committed** tree is 9 999 347 bytes (9.54 MiB). The filesystem and the Git object sizes agree, so this
is not a checkout artefact: the recorded figure was never the committed one (it is 3 895 bytes high, most
likely measured mid-wave-F before a final file write, then copied forward). Four documents carried it, the
report was about to, and the honest disposition is a correction plus a rule.

**Rule restated (third occurrence of this class).** Every figure that describes an artefact is produced by a
command in the same session that writes it down. Where the artefact is under version control, the figure is
verified against the committed tree (`git ls-tree -r -l`), not only against the working directory, the two
can disagree, and only one of them is what a reader checking out the repository will see.

Same close, two more transcription errors caught before publication rather than after: the report's first
draft carried Ridge MAE/RMSE as 73.5/96.3 and random forest as 41.6/62.4; the measured values are
**69.93/94.91** and **39.03/60.63**. The published table carries the measured ones. The pattern is the same
in all four cases, the numbers felt known, and it is the reason §10 of the report states the rule rather
than only the results.

## Phase 6: the audit (2026-10-07, final phase)

No `src/` or `tests/` line changed in this phase, so there is no RED→GREEN unit to record: the phase is a
read-only audit plus the document corrections it forced. What the audit did **not** find is as important as
what it did: **no critical failure in the shipped artefacts**, no dead code, no unlabelled artefact, no
failing test, and no claim in `report.md` that the artefacts do not support.

What it did force:

* fifteen traceability rows refreshed (R10, R22, R24, R25, R27, R29, R31, G-L3, G-L10, G-L14, G-L22, G-L24,
  G-L28, G-L30, G-L33, G-P-3, G-P-5, G-P-6, G-P-R), several had been showing a pending sub-state for work
  that was already delivered;
* three stale eval-harness rows closed (E19, E33, E36–E37);
* the harness count re-derived by parsing cells after two keyword-grep counts disagreed, the audit's own
  numbers are held to the rule the project adopted for documents (G8 / P4-2 / P5-1): a number is copied from
  a command;
* one self-correction inside the audit's own prose (a claimed third sandbox restart that had not happened);
* posteriors recorded in `docs/notebook/calibration.md`, including a pre-registered prediction (CAL-4) scored
  as **wrong**, rather than editing the frozen preregistration whose hash is the proof of freezing.

The one PARTIAL verdict in the audit's Part A is reserved for the thing this project kept getting wrong and
could not test its way out of: numbers that live in prose. The rule is written down; the honest position is
that a rule is weaker than a test, and that is what PARTIAL means here.

## Post-audit: a documentation-only change has no RED state (2026-10-07)

The project's rule is RED before GREEN for every behavioural change. This pass changed no behaviour: it
rewrote `README.md` and `report.md`, replaced 607 em dashes across 27 documents, and edited seven comments
or docstrings in `src/config.py`, `tests/conftest.py` and `tests/test_properties.py`. No test asserts document
prose (checked by grepping `tests/` for README and report assertions), so there is nothing that could fail
first, and inventing a failing test for punctuation would be theatre.

What stands in place of a RED state, and what it caught:

* the sweep tool refuses to write a file whose numeric tokens would change, checked per file;
* table structure was compared against the committed version by pipe counts, and `report.md` is back to 77
  table rows because the schema table in section 5 was restored rather than left as prose;
* a diff-aware scan for comma splices introduced by the sweep found 15 candidates, of which 9 were created
  here and were re-punctuated by hand;
* the content guard was re-run on `report.md` and is clean;
* the full gate was re-run after the last edit: `ruff` clean, `mypy` clean on 21 files, **343 passed,
  0 skipped in 304.95 s**, coverage **100 %** (1388 statements / 336 branches), the same counts as the
  Phase-6 gate.

Two strings in `src/sensitivity.py` were deliberately left alone. Both are embedded in the committed
`results/sensitivity/sensitivity_metadata.json`, so rewording them would have desynchronised the artefact from
the code; the alternative, re-running the sweep, would have changed a measured `runtime_s` to buy nothing.
`tools/humanize_dashes.py` was deleted with the other process notes; the pass's report is reproduced in
`docs/notebook.md`, and six hash-pinned documents (103 em dashes) were excluded from that pass on purpose.
