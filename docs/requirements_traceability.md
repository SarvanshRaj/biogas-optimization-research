# Requirements and where each one is met

Every requirement this project was asked for, with the artefact or test that satisfies it. Statuses are
`IMPLEMENTED`, `MET` (a research requirement, satisfied), or `NOT APPLICABLE` with the reason given. Nothing
here is marked satisfied on the strength of a claim: the evidence column names a file, a test or a command.

Last re-audited on 2026-10-07, after the documentation trim described in `docs/notebook.md`. No requirement
was dropped by that trim; two evidence pointers were moved to surviving files.

## 1. Requirements

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| R1 | Follow the project instructions received in the conversation | IMPLEMENTED | Provenance caveat in `docs/notebook.md`: the instructions arrived as pasted text, so byte-identity cannot be verified |
| R2 | A traceability table with exact evidence per requirement | IMPLEMENTED | This file |
| R3 | Subtopics added mid-run get recorded and processed, not dropped | IMPLEMENTED | The readability pass and the delivery change are dated in `docs/notebook.md` |
| R4 | Work in phases, one at a time, with a status stop at the end of each | IMPLEMENTED | The phase table in `docs/notebook.md` |
| R5 | Inspect the repository and the project's rules before writing anything | IMPLEMENTED | `docs/notebook.md` section "What was here at the start": tree, history, licence, CI, remote |
| R6 | Record the searches run and the sources retrieved, with a verification status | MET | `docs/literature_review.md`, `docs/references.md`, `docs/sources.json` |
| R7 | Keep a running record of decisions and changes | IMPLEMENTED | `docs/notebook.md`, `docs/preregistration.md`, `docs/preregistration_addendum_01..03.md` |
| R8 | Write for an ISC Class XII reader as well as for a reviewer | IMPLEMENTED | `report.md` section 12: plain-language explanation plus 10 viva questions with answers |
| R9 | Simulation only, no invented experimental data, no claimed real yields | IMPLEMENTED | Every artefact carries `SIMULATED`; `tests/test_content_guard.py` enforces it |
| R10 | Do not imply the 2025 Sakura Science programme included this software | IMPLEMENTED | README section "The 2025 programme"; `report.md` section 1 |
| R11 | Check parameters and concepts against retrievable sources before modelling | MET | `docs/literature_review.md`, `docs/parameter_table.md` |
| R12 | Cite every literature-based range from an opened source; never invent citations or DOIs | MET | 32 records with locators and statuses in `docs/sources.json`; one paywalled standard recorded as `UNVERIFIED` |
| R13 | Label every parameter `direct`, `analogous` or `ASSUMPTION FOR SIMULATION`, with a sensitivity range | MET | `docs/parameter_table.md`, enforced by `tests/test_train_models.py` schema tests |
| R14 | Do not confuse ambient relative humidity with slurry moisture or total solids | MET | RH is excluded; the reason is in `docs/parameter_table.md` |
| R15 | Computational only: nothing that teaches culturing, vessels, gas handling or digester operation | IMPLEMENTED | `tests/test_content_guard.py`: 9-pattern denylist, tested against planted violations |
| R16 | Say that a model trained on the simulator learns the simulator | MET | README, `report.md` sections 7 and 9, and every results table's `SIMULATED` marker |
| R17 | Answer the five research questions before writing the main code | MET | `docs/preregistration.md`, section 6 |
| R18 | Transparent generator: documented parameters, fractions in [0, 1] summing to 1, declared TS, no unexplained variables | IMPLEMENTED | `docs/model_specification.md`; bounds and sum-to-one asserted in `tests/test_simulate_data.py` |
| R19 | Exactly five models: dummy mean, Ridge, RandomForest, gradient boosting, small MLP | IMPLEMENTED | `config.MODELS`; the count is asserted in `tests/test_train_models.py` |
| R20 | Grouped split, train-only fitting, tuning inside train and validation, test opened once, five seeds reported as mean and spread | IMPLEMENTED | `tests/test_preprocess_leakage.py`, `tests/test_evaluate.py`; results in `results/metrics_summary.csv` |
| R21 | Optimiser: simulator objective only, mixture sums to 1, bounds and stability constraints, baseline comparison, perturbation test, explicit warning that the optimum is not a recipe | IMPLEMENTED | `src/optimize.py`; `results/optimisation/`; `report.md` section 8 |
| R22 | Repository discipline: inspect first, do not overwrite, isolated branch, clean diff, no push without approval | IMPLEMENTED | The assistant pushed nothing; the delivery was a files-only archive, which the author then published to `main` on GitHub himself |
| R23 | Clean-checkout reproduction: bounded pins, CI file, README run commands | IMPLEMENTED | `requirements.txt`, `.github/workflows/ci.yml`, README section "Running it", `results/README.md` |
| R24 | Concise prose, explain every change, disclose AI assistance, no detector evasion | **NOT MET: the disclosure was withdrawn by the author on 2026-10-08** | The disclosure paragraphs in `README.md` and `report.md` were removed at the author's request, so no document now carries one. The prose and no-detector-evasion halves of this row still hold |
| R25 | Test-first development, a test plan before coding, property-based and regression tests, static checks, 100 % statement and branch coverage on the core | IMPLEMENTED | `docs/tdd_log.md` (RED before GREEN, per wave), `docs/test_matrix.md`, `tests/` (14 modules, 343 tests), coverage at 100 % |
| R26 | The required file set: README, dependencies, `src/*.py`, `tests/`, workflow, synthetic data, results, report, docs | IMPLEMENTED | All present; the one planned module that was not built is listed in section 2 |
| R27 | The report has the twelve numbered sections in order | IMPLEMENTED | `report.md`; the order was checked by section scan |
| R28 | `SIMULATED` on every figure, CSV, metric and metadata field | IMPLEMENTED | Guard tests over `results/` and `data/synthetic/` |
| R29 | A PASS/FAIL self-check at the end | IMPLEMENTED | `docs/phase6_audit.md`, 14 items with verdicts and evidence |
| R30 | Legal and regulatory scope | NOT APPLICABLE | Pure computation on synthetic arrays: no human or animal subjects, no personal data, no regulated laboratory work |
| R31 | Third-party figure and text reuse | NOT APPLICABLE | Sources are cited and described; no third-party figure or table is reproduced |
| R32 | Documentation volume proportionate to a solo, non-public project | IMPLEMENTED | Working-note files removed; what survives is listed in `docs/notebook.md`; the counts are in that file |
| R33 | Delivery as a files-only archive | IMPLEMENTED | The archive, its build command and its size are recorded in `docs/notebook.md` |

## 2. Where the plan and the build differ

| Planned | Built | Why |
|---|---|---|
| `src/pipeline.py`, a single entry point chaining the study | Five CLIs, chained end to end by `tests/test_integration_e2e.py` | Each step stays independently runnable and testable; the chained test proves they compose. No wrapper was added, because the study is reproduced by the commands in `results/README.md` |
| A single `docs/notebook/` tree holding every working note | `docs/notebook.md` plus the records that carry evidence | The working notes were process commentary. Their content either moved to a surviving file or was dropped; the mapping is in `docs/notebook.md` |
| Ten-assumption sweep at study size | Sweep run at the declared smaller size | Runtime on 2 vCPU; the size is recorded with the results and the conclusion is stated with that limit |

## 3. Known weaknesses

Named here rather than left for a reader to find: the simulation proves nothing about real digesters; the
literature does not contain the exact two-stage concept, so the pre-treatment factor is an assumption with a
wide range; the optimiser's best mixture is an artefact of the simulator and fails its own perturbation test;
the GitHub Actions workflow has never executed; mutation testing was done by hand, four mutants in the final
wave, with no mutation tool available; and the sandbox restarted twice during the work, which is why the
commit history contains a labelled recovery commit.
