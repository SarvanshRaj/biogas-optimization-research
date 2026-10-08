# Test matrix, acceptance tests, module coverage plan, eval-harness mapping

**Companion to:** `docs/preregistration.md` (locked `PREREG_V1`) · **Label:** INTERNAL · **Date:** 2026-10-07
**Purpose:** every module, function, branch, validation rule and error path is mapped to a test ID *before*
implementation. Phase 3 writes these tests first (RED), then implements to pass them (GREEN). A line that
cannot be covered is a blocker unless you approve a written exclusion.

Test-ID families: `R-*` research · `D-*` development (unit/integration/CLI/schema) · `HYP-*` property-based ·
`P-*` prompt/child-artifact · `AIW-*` AI-writing · `SK-*` skills · `HP-*` hyper-personalisation ·
`U-*` UGC · `RH-*` rabbit-hole/iceberg · `AR-*` access resilience · `CU-*` catch-up · `QE-*` query expansion.

---

## 1. Development tests (D-*)

### 1.1 Configuration, `src/config.py`

| ID | Target | Behaviour asserted | Type |
|---|---|---|---|
| D-CFG-01 | `Config` defaults | Default seed, ranges, and scenario/row counts match the documented values exactly | unit |
| D-CFG-02 | Seed override | Passing a different seed changes the resolved config object; the default stays immutable | unit |
| D-CFG-03 | Range consistency | Every declared range is finite, `low < high`, and inside a global plausibility envelope | unit |
| D-CFG-04 | Unit field present | Every parameter exposes unit + `source_class`; unknown class raises | unit |

### 1.2 Simulator, `src/simulate_data.py`

| ID | Target | Behaviour asserted | Type |
|---|---|---|---|
| D-GEN-01 | `generate_dataset(seed)` | Identical seed ⇒ byte-identical DataFrame (hash equality) | unit |
| D-GEN-02 | `generate_dataset` different seeds | Different seed ⇒ different values, but identical schema/shape | unit |
| D-GEN-03 | Scenario design | Exactly `n_scenarios × replicates` rows; each `scenario_id` appears exactly `replicates` times | unit |
| D-GEN-04 | No hidden global RNG use | Two generators with the same seed, created in different orders, agree (no reliance on `np.random` global state) | unit |
| D-GEN-05 | Row-level isolation | Mutating a returned frame does not affect a subsequent call | unit |
| D-VAL-01 | Fractions in range | All carbohydrate/protein/lipid fractions ∈ [0, 1] | unit + HYP-01 |
| D-VAL-02 | Fractions sum to 1 | Each row's three fractions sum to 1 within 1e-9 | unit + HYP-02 |
| D-VAL-03 | Boundary fractions | Rows with a fraction at 0 and at 1 are produced and remain valid | unit |
| D-VAL-04 | Total solids in range | Total solids within its declared range for every row | unit |
| D-VAL-05 | Process variables in range | Temperature, pH, OLR, HRT, I:S ratio, pre-treatment inputs all inside declared ranges | unit + HYP-03 |
| D-VAL-06 | NaN rejected | NaN in any required field raises a typed validation error naming the field | unit |
| D-VAL-07 | Infinity rejected | `±inf` rejected the same way | unit |
| D-VAL-08 | Missing field rejected | A dropped column raises with the column name in the message | unit |
| D-VAL-09 | Wrong type rejected | Strings/objects where floats are required raise a typed error | unit |
| D-VAL-10 | Empty input rejected | Zero-row and zero-column frames raise | unit |
| D-VAL-11 | Duplicate columns rejected | Duplicated column names raise | unit |
| D-VAL-12 | Out-of-range rejected | Values just outside each bound raise; values exactly on the bound pass | unit |
| D-VAL-13 | Message quality | Every validation error message names the offending field and the expected range | unit |
| D-VAL-14 | Unknown extra column | Unexpected column rejected (schema is closed) | unit |
| D-VAL-15 | Unit consistency | Asserted units for each column stay constant across schema evolution checks | unit |
| D-VAL-16 | Pre-treatment separation | Pre-treatment fields and AD fields are disjoint name-sets; a duplicate name across the two groups raises | unit |
| D-MB-01 | Output bounds | `simulated_methane_yield`/`simulated_yield_index` ∈ [0, 100]; methane fraction ∈ (0, 1); no negative biogas volume | unit + HYP-04 |
| D-MB-02 | Monotone composition response | Holding others fixed, increasing a high-lipid fraction past the inhibition threshold does not increase yield (shape check, not a biological claim) | unit |
| D-MB-03 | Monotone process response | Yield at the declared optimum exceeds yield at the extremes of both temperature and pH (unimodality) | unit |

### 1.3 Schema, serialisation, artefacts

| ID | Target | Behaviour asserted | Type |
|---|---|---|---|
| D-SCH-01 | Column order/dtypes | Generated frame has exactly the documented columns, order, and dtypes | unit |
| D-SCH-02 | Data dictionary parity | Every column in the CSV appears in `data/synthetic/data_dictionary.md`, with unit + provenance | unit |
| D-SCH-03 | CSV round-trip | Write → read returns an equal frame (dtype-aware compare) | integration |
| D-SCH-04 | SIMULATED labelling | CSV sidecar/metadata and figure titles carry the SIMULATED marker; metrics JSON carries `data_provenance: synthetic` | integration |
| D-SCH-05 | Model persistence | Fitted model save → load → predictions identical (all five models where serialisable) | integration |
| D-SCH-06 | Physical-unit guard, **conditional gate fired "yes"** (Addendum 02 §A2.1) | Given any artifact declaring a methane yield in `mL CH4/g VS`: assert (a) the `SIMULATED` marker is present, (b) the scale-adoption note naming CIT-0004 is present, (c) an explicit statement that no BMP protocol is implemented is present | integration |

### 1.4 Splitting and preprocessing (leakage guards)

| ID | Target | Behaviour asserted | Type |
|---|---|---|---|
| D-SPL-01 | Group disjointness | `set(train.scenario_id) ∩ validation == ∅`, `∩ test == ∅`, `validation ∩ test == ∅` | unit |
| D-SPL-02 | Coverage | Every scenario lands in exactly one split; split sizes match the declared ratios ±1 scenario | unit |
| D-SPL-03 | OOD family held out | The designated high-lipid scenario family appears in the OOD probe set and nowhere in training | unit |
| D-SPL-04 | Determinism | Same seed ⇒ identical split membership | unit |
| D-SPL-05 | Non-random-index guard | Split is not reproducible by `train_test_split` on row indices alone (demonstrates rows were not scattered) | unit |
| D-PRE-01 | Fit-on-train-only | Transformer parameters (means/scales) equal those computed from train alone; explicit mutation test: perturbing test rows does not change fitted transformer values | unit |
| D-PRE-02 | Pipeline encapsulation | Scaling never applied to the raw frame handed to evaluation; only pipeline outputs are scored | integration |
| D-PRE-03 | Constant column safety | A constant feature survives preprocessing without producing NaN/inf | unit |

### 1.5 Models

| ID | Target | Behaviour asserted | Type |
|---|---|---|---|
| D-MOD-01 | Five models present | Registry exposes exactly Dummy, Ridge, RandomForest, HistGradientBoosting, MLP | unit |
| D-MOD-02 | Fit + predict shape | Each model fits on synthetic train data and returns predictions of length `n_test` | unit |
| D-MOD-03 | Finite predictions | No NaN/inf predictions from any model on any fold | unit |
| D-MOD-04 | Determinism | Same seed ⇒ identical predictions (MLP seeded; tree `random_state` set) | unit |
| D-MOD-05 | Dummy baseline sanity | Dummy predictions are constant and equal to the train mean | unit |
| D-MOD-06 | Hyperparameter tuning scope | Tuning touches only train/validation folds; a test that fails if the test fold is passed to the search | unit |
| D-EDGE-01 | Tiny dataset | All models run on the smallest legal dataset (2 scenarios) without crashing | unit |
| D-EDGE-02 | Constant target | Constant target produces no exception; R² handling is defined and asserted | unit |
| D-EDGE-03 | Single-feature dataset | Models run when only one feature column is present | unit |
| D-EDGE-04 | Collinear features | Duplicated feature columns do not break Ridge (singular-matrix safety) | unit |
| D-EDGE-05 | MLP-specific | Converges (no `ConvergenceWarning` escalated to failure) on the standard config, or the warning is explicitly asserted and run time bounded | unit |
| D-EDGE-06 | Empty test fold | Zero test rows raises a clear error rather than returning NaN metrics | unit |

### 1.6 Metrics and reporting

| ID | Target | Behaviour asserted | Type |
|---|---|---|---|
| D-MET-01 | RMSE hand-computed | `rmse([1,2,3],[1,2,4]) == sqrt(1/3)` exactly | unit |
| D-MET-02 | MAE hand-computed | Known vector ⇒ known MAE | unit |
| D-MET-03 | R² hand-computed | Perfect prediction ⇒ 1.0; mean prediction ⇒ 0.0 | unit |
| D-MET-04 | R² undefined | Constant truth ⇒ R² reported as undefined/`None` with an explicit flag, never as a silently wrong number | unit |
| D-MET-05 | Degenerate input | Empty arrays raise; single-row input returns 0.0 MAE/RMSE | unit |
| D-MET-06 | Multi-seed aggregation | Mean and sample SD computed over seeds match a hand-computed example | unit |
| D-REP-01 | Comparison table | Table contains every model × metric × seed, with baseline row first | integration |
| D-REP-02 | Plots written | Residual and predicted-vs-true figures exist, non-empty, with SIMULATED in the title | integration |
| D-REP-03 | OOD report | OOD probe metrics appear in the results artifact and are labelled as extrapolation | integration |

### 1.7 Optimiser

| ID | Target | Behaviour asserted | Type |
|---|---|---|---|
| D-OPT-01 | Mixture constraint | Any returned solution has fractions summing to 1 within 1e-6 | unit |
| D-OPT-02 | Bounds | Every returned fraction ∈ [0.02, 0.90]; process settings inside declared bounds | unit + HYP-05 |
| D-OPT-03 | Feasibility constraint | Stability indicator of the returned solution is inside the feasible region; an intentionally infeasible candidate is rejected | unit |
| D-OPT-04 | Boundary optimum | On a constructed surface whose true optimum is on the fraction boundary, the solver returns a boundary solution within tolerance | unit |
| D-OPT-05 | Infeasible problem | If all candidates violate the stability constraint, the function reports infeasibility explicitly (no exception, no fake answer) | unit |
| D-OPT-06 | Reproducibility | Same seed ⇒ identical recommendation | unit |
| D-OPT-07 | Perturbation robustness | ±5 % perturbation harness returns a fraction-inside-region statistic in [0, 1] with the documented denominator | unit |
| D-OPT-08 | Baseline comparison | The equal-thirds baseline is evaluated with the same scoring path and reported beside the optimum | integration |

### 1.8 CLI and end-to-end

| ID | Target | Behaviour asserted | Type |
|---|---|---|---|
| D-CLI-01 | Subcommands | `generate`, `train`, `evaluate`, `optimize`, `all` each run and exit 0 on defaults | integration |
| D-CLI-02 | `--seed` | Changing `--seed` changes the artefact hash; repeating it reproduces it | integration |
| D-CLI-03 | Bad input | Unknown subcommand / non-integer seed / bad path exits non-zero with an actionable message | CLI |
| D-CLI-04 | Small end-to-end | Full pipeline on a reduced config writes data, metrics, figures, and a report fragment | integration |
| D-CLI-05 | Idempotence | Re-running without `--force` does not corrupt or duplicate artefacts | integration |

### 1.9 Documentation and repo

| ID | Target | Behaviour asserted | Type |
|---|---|---|---|
| D-DOC-01 | Content guard | README/report/module text contains no operational culturing, pressure-vessel, gas-handling or digester-operation instructions, and no phrase asserting real yields | integration (denylist scan) |
| D-DOC-02 | Disclaimer presence | README + report assert that models learn the simulator's assumptions and that the optimiser's recipe is simulator-specific | integration |
| D-DOC-03 | Reproducibility block | README's documented commands execute in a clean checkout to regenerate every committed artefact | manual + CI |
| D-REPO-01 | CI workflow | Workflow file is valid YAML and runs tests + lint on push | integration |
| D-REPO-02 | Pins | Dependency versions are bounded/pinned and match the versions recorded in the run log | unit |
| D-REPO-03 | Ignore rules | Generated heavy artefacts are gitignored; synthetic CSVs that are committed stay small and labelled | unit |

### 1.10 Property-based tests (`HYP-*`, Hypothesis)

| ID | Property |
|---|---|
| HYP-01 | For any generated batch, all fractions ∈ [0, 1] |
| HYP-02 | For any generated batch, fractions sum to 1 within tolerance |
| HYP-03 | For any in-range parameter vector, the simulator returns finite, bounded outputs |
| HYP-04 | Yield index is non-decreasing under availability gain (monotonicity) and bounded above by the declared ceiling |
| HYP-05 | For any feasible mixture produced by the sampler, the constraint checker accepts it; for any violating vector, it rejects it |
| HYP-06 | Validation never mutates its input frame |

## 2. Research tests (`R-*`), locked before Phase 1

| ID | Assertion that must hold before Phase 5 closes |
|---|---|
| R-Q1 | Every declared input variable has a stated role and a source or an **ASSUMPTION FOR SIMULATION** label |
| R-E1 | Each load-bearing parameter range is supported by ≥ 1 retrieved source, or explicitly labelled an assumption with a sensitivity range |
| R-E2 | Redundancy check: OLR vs TS and I:S vs OLR pairs are either shown non-redundant for the model or collapsed to one variable with the reason recorded |
| R-F1 | The *A. oryzae* / food-waste search is run to exhaustion (including contrary and failure queries); the outcome, including "no food-waste evidence found", is recorded |
| R-F2 | The pre-treatment representation is shown to span harmful, neutral and beneficial regimes in the generated data |
| R-C1 | Every literature-derived number in the report resolves to a retrieved record whose title/first-author/year match and whose cited section supports the sentence |
| R-C2 | Any citation that cannot be retrieved is marked UNVERIFIED and excluded from Key Findings |
| R-U1 | UGC pass covers ≥ 3 platform classes, popular and long-tail, with "searched, not found" recorded where applicable |
| R-U2 | UGC items are labelled context-tier; no constant in the simulator rests on UGC |
| R-RH1 | Iceberg layers L0–L3 documented with at least one contested (L3) branch engaged |
| R-RH2 | Rabbit-hole queue has ≥ 7 entries with status and stop reasons; majority closed |
| R-B1 | Multilingual/geography pass attempted (Hindi/regional terms, Indian institutional sources) with coverage stated |
| R-B2 | English-dominance limitation of the AD literature stated explicitly |
| R-I1 | Every external text handled as DATA; injection attempts quarantined and logged; none obeyed |
| R-D1 | Phase 5 presents 2–4 options with upside, downside, reversibility, first cheap test, kill criteria |
| R-X1 | The audit reports every change made after the plan was written |

## 3. Prompt / child-artifact tests (`P-*`)

| ID | Assertion |
|---|---|
| P-1 | Child template runs standalone for its purpose with no parent file present (checked by reading only the child) |
| P-2 | Child contains executable procedures (phase gates, stop conditions, contracts), not gene names or stamps |
| P-3 | Child carries the recursive clause: prompts *it* generates must also fully implement the same body pattern |
| P-4 | Child embeds citation verification, injection defence, tests-first, discovery, uncertainty and audit procedures |
| P-5 | Child marks inapplicable genes explicitly (never silently omitted) |
| P-6 | PE lint passes: sections delimited, output contract exact, degrade paths, eval hooks ≥ 3, uncertainty permitted |
| P-7 | Atomic slots all filled or explicitly N/A; one named framework preset with rationale |
| P-8 | Emission checklist completed with every row PASS before delivery |

## 4. Self-check

The end-of-study checklist and its verdicts live in `docs/phase6_audit.md`. Its items cover the code, the
data, the claims and the process: nothing in it is scored favourably for being stated confidently.

## 6. Coverage policy and evidence

| Item | Rule |
|---|---|
| Core modules requiring 100 % statement + branch | `config`, `simulate_data` (incl. validation), split/preprocessing, `train_models`, `evaluate`, `optimize`, CLI entry point |
| Non-core (allowed below 100 % with explicit note) | plotting helpers where a branch is pure matplotlib styling; `__main__` glue |
| Exclusions | Only with a written reason and your approval, recorded here |
| Changed-line coverage | Reported per phase 3–4 commit |
| Mutation testing | `mutmut` attempted in Phase 4; if unavailable or unusable in this sandbox, reported as **RUN-BLOCKED** with the exact command and the surviving-mutant status unknown |
| Evidence | `docs/tdd_log.md` records RED-before-GREEN per work unit: test ID, command, observed failure, then observed pass |
| Static checks | `ruff format --check`, `ruff check`, `mypy src` (best effort; failures reported honestly rather than hidden) |

## 7. RED evidence plan (what Phase 3 must show before implementing)

1. Write `tests/` covering §1 in order: config → validation → generation → split/preprocessing → models →
   metrics → optimiser → CLI.
2. Run `pytest -q` **before** implementing each module; capture the failure output into the RED-evidence
   log (`docs/tdd_log.md`)
   (this is the RED evidence; without it the work is not TDD-complete).
3. Implement the minimum that turns the target tests green.
4. Refactor only with the suite green; re-run and append evidence.
5. Record the exact commands, pass/fail counts, coverage and any blocked check in `docs/tdd_log.md`.

---

*This matrix is the locked acceptance-test set for Phases 3–4. Any test added after Phase 2 is labelled
**AD_HOC** with a reason, per the change protocol in `docs/preregistration.md` §11 P10.*
