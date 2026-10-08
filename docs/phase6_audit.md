# Phase 6: hard audit

**Date:** 2026-10-07 · **Subject:** the whole project, as shipped · **Method:** read-only re-derivation
with fresh commands; every verdict carries evidence that can be re-run.
**Verdicts used:** **PASS** · **PARTIAL** · **FAIL** · **RUN-BLOCKED** (attempted, blocked by the
environment, reported) · **N/A** (not applicable, with the reason). No item is left unmarked.

> **SIMULATED.** Everything audited here is a computational artefact built on synthetic data. A
> "PASS" in this document means *the process and the software did what they claimed*, never that a
> real digester behaves as the simulator says. Any real-world claim in this project remains
> untested by construction.

## 0. What this audit is

The 14 self-check items in Part A are derived from the requirements listed in
`docs/requirements_traceability.md`: scope honesty, simulation-only discipline, numbers that were actually
measured, plan integrity, test-first evidence, coverage, leakage, model-set discipline, protocol,
optimiser honesty, labelling, reproducibility, report completeness, and blocked items reported rather than
hidden. The item numbering is mine and is stated rather than hidden.

The audit then walks every requirement row (Part B), two further checks that do not fit Part A (Part C),
and the repository review (Part E). A superset can miss nothing that a subset would catch.

## Part A: the 14 derived self-check items

| # | Self-check item | Verdict | Evidence (re-runnable) |
|---|---|---|---|
| 1 | **Scope honesty**: no experimental claim, no real yield, no implication that the 2025 programme included this work | **PASS** | `report.md` header + §1; README §"Earlier programme concept (2025)"; the guard's label test; no figure or CSV states a measured yield |
| 2 | **Simulation-only discipline**: no operational content anywhere published | **PASS** | `tests/test_content_guard.py`: 9-pattern denylist, 15 tests, tested against 5 planted violations; sweeps `report.md`, `results/`, `data/synthetic/` and fresh pipeline output. Three real catches: P4-1 (missing provenance), one denylist phrase in the report, and the missingness-wording gap |
| 3 | **Every number in a document is measured** | **PARTIAL → fixed in this phase** | Three violations found and corrected: G8 (mutation counts never observed), P4-2 (`results/` 17 files/632 KiB vs measured 16/610.0 KiB), P5-1 (dataset 10 003 242 bytes vs measured, Git-verified 9 999 347 bytes), plus two MAE/RMSE values in the report's first draft. The rule now stands in `docs/tdd_log.md` and report §10. **PARTIAL, not PASS, because the failures were mine and were caught by chance, not by an automated check**: prose numbers have no test |
| 4 | **Plan integrity and drift** | **PASS** | The research questions, falsifiers, thresholds and decision rules written before the study ran are still the ones in force; the edits made since (wording, file paths, the documentation trim) are listed in `docs/notebook.md`, and none of them touches a question or a threshold |matrix `daf48788`, all unchanged. Post-freeze deviations are labelled AD_HOC where they exist, and the one unbuilt preregistered deliverable (`src/pipeline` CLI) is a **declared deviation**, not a silent omission |
| 5 | **Tests first (RED before GREEN)** | **PASS** | Six waves with recorded RED evidence in `docs/tdd_log.md` (e.g. wave G: 36 failed / 4 errors before the module existed; wave C: `ModuleNotFoundError`, 18 failed / 14 errors). The one test-only change (CLI chain, four→five) is labelled as having no RED to show rather than dressed up |
| 6 | **Coverage and static checks** | **PASS** | 343 passed / 0 skipped; **100 % statement + branch** on `src/` (1388 stmts / 336 branches, 0 missed, 0 partial); `fail_under = 100` never lowered; one declared exclusion (entry-point guard); ruff and mypy clean (21 files); changed-line coverage 100 % (every `src/` line is new relative to `main`'s single commit) |
| 7 | **Leakage and split discipline** | **PASS** | Scenario-grouped 70/15/15 with all 8 replicates kept together; group-overlap asserted; latent factors never written to the model-facing file (column-denylist test); preprocessing fitted on train only (asserted, mutation-tested in wave D); permuted-target negative control; near-duplicate rows checked so rounded inputs cannot straddle splits |
| 8 | **Model-set discipline** | **PASS** | Exactly five models, DummyRegressor, Ridge, RandomForest, HistGradientBoosting, small MLP, fixed in SPEC_V1 before training; no additions, no padding, no post-hoc selection |
| 9 | **Protocol compliance** (grouped split, train-only fitting, tune inside train/validation, test opened once, ≥5 seeds, mean ± spread, CIs only with assumptions, baseline, residual + predicted-vs-true plots, importance labelled simulator-descriptive, OOD check, extrapolation limits stated) | **PASS** | `results/metrics_summary.csv` (5 seeds, mean/std/min/max/n_finite), `results/figures/*`, `results/metrics_ood.csv`; the report states the spread is descriptive, not inferential |
| 10 | **Optimiser honesty**: constraints enforced beyond yield, baseline compared, perturbation robustness, exploitation warned, F5 applied | **PASS** | C-a…C-f enforced by penalty + a raising assertion; D6 baseline reported infeasible with its pre-declared feasible projection; ±5 % perturbation reported per arm; **F5 fired on the oracle in both tiers → the optimum is reported artefactual and no best recipe is claimed** |
| 11 | **Labelling**: SIMULATED on every figure/CSV/metric/metadata | **PASS** | Guard tests: every results and dataset CSV row carries `simulated: true` + simulator version; every JSON sidecar declares provenance; `[SIMULATED]` in figure titles, CLI output and the optimiser caveat; the report carries the marker in a scope block and in every results table |
| 12 | **Reproducibility** | **PASS (with two reported limits)** | Commands, versions, runtimes, artefact inventory and frozen hashes are in report §10 and `results/README.md`; the evaluation reproduces the Phase-3 probe exactly; limits reported: (a) the GitHub Actions workflow has **not been executed** (RUN-BLOCKED: the platform API returned 403 for the permissions check), (b) commit identifiers are clone-local because two sandbox re-clones flattened history |
| 13 | **Report completeness and teaching material** | **PASS** | Section scan of `report.md`: `## 1.`…`## 12.` present in the frozen order; the parameter table carries value/unit/source/uncertainty; **10** viva Q&A (requirement 8–10); plain-language explanation present; AI-assistance disclosure in the header |
| 14 | **Blocked and unverifiable items reported, not hidden** | **PASS** | This document, section 6; the paywalled standard CIT-0017 recorded as UNVERIFIED; the RUN-BLOCKED/UNVERIFIED items are named in the ledger, the harness and the report rather than smoothed over |

Two of the fourteen are not clean PASS: **#3** (numbers in prose, a process failure with a fix and a rule)
and, in the same family, item #12's two environmental limits.

## Part B: requirement rows

Status at this audit: **31 IMPLEMENTED or MET · 2 NOT APPLICABLE (R30 legal scope, R31 reuse licensing) ·
0 PENDING · 0 FAIL.** Several rows still showed a pending sub-state from an earlier phase when the audit
began (the report format, the audit itself) and were corrected here against the artefacts rather than left
standing.

## Part C: two further checks

| Check | Verdict | Evidence |
|---|---|---|
| Citation integrity | **PASS (one named gap)** | 32 records with locator and status in `docs/sources.json`: 5 `V-FULL`, 9 `V-META`, 17 `PARTIAL`, 1 `UNVERIFIED` (the paywalled standard, named as a gap rather than used as a source) |
| Mutation-testing status | **PARTIAL, reported** | Hand-inserted mutants only, no tool available: 4 mutants in the final wave, 4 killed, each with the observed failure counts recorded in `docs/tdd_log.md` |

## Part E: repository review

| Check | Result |
|---|---|
| Diff scope | Every phase's staged diff was reviewed before committing: this audit touches only `docs/`, **no `src/`, no `tests/`, no `results/` change** |
| Unrelated edits / dead code | None found; the phase diffs contain only the changes described in their commit messages and log entries |
| Secrets / credentials | Pattern sweep over the committed diff (`api_key|token|password|secret|PRIVATE|ghp_|sk-`): clean at every commit |
| Personal data | Author's name only; no contact details, no personal identifiers, no third-party personal data |
| Oversized artefacts | Largest committed files are the five dataset CSVs (~1.7 MB each); `data/synthetic/` is 9.54 MiB in total and is the study's deliverable, committed deliberately with the two `.gitignore` exceptions removed as the recorded rule said they would be |
| Generated files needing ignore rules | `results/` is a deliverable and is committed on purpose; caches and coverage files stay ignored |
| Working tree at the close | clean; remote `main` untouched at `4c3c9cf` (push not approved) |

## §6: critical failures, fixes made here, and what remains blocked

**Critical failures found in the shipped artefacts: none.** The failures this project actually had were
found and fixed *during* the phases, not at the audit, and they were all of one family: **numbers written
from expectation rather than measurement** (G8, P4-2, P5-1, two MAE/RMSE values). Each has a correction in
place, a regression test where a test could carry one (P4-1's provenance test), and, where a test could
not carry one (prose), a written rule.

Fixes made **in this phase**: the stale status rows listed in Part B; the three stale harness rows in
the posteriors recorded in this section rather than by editing a document written earlier
(making the point that freezing is verified by hashes, not honoured by memory).

**Residual blockers, carried openly:**

1. **Push is not approved**: the remote `main` is still `4c3c9cf`; the entire project lives on the
   session branch, locally. Nothing here is published.
2. **CI has never run** (RUN-BLOCKED): the workflow is committed, the permissions check returned 403.
3. **Tool-based mutation testing was not run**; only hand-inserted mutants.
4. **The brief's 14-item enumeration is not stored in this repository** (see §0), the audit covers a
   superset and says how the 14 were derived.
5. **Two sandbox re-clones flattened local history**; commit identifiers are clone-local and per-wave
   granularity before Phase 4 is unrecoverable. The *content* survives; the history does not.
6. **The MLP does not converge** (5 of 5 seeds) and is reported as such.
7. **The preregistered `src/pipeline` CLI does not exist**; five CLIs are chained by a test instead.

## §7: confidence-rated grade and the weakest-claim autopsy

**Grade, split by what is being graded:**

| Target | Confidence | Why |
|---|---|---|
| The software, the protocol and the honesty of the reporting | **9/10** | 343 tests with 100 % statement+branch coverage, independent re-derivations (anchor checks, per-seed MLP re-fit, Git-verified byte counts), pre-declared rules applied against the project's own headline result, and four documented self-corrections |
| The simulated results as statements about the simulator | **8/10** | The ground truth is fully specified, seeded and reproducible; the remaining uncertainty is the specification's own internal inconsistency (anchors) and the contested TS direction |
| Any extrapolation to real food waste or real digesters | **1/10, by construction, and correctly so** | Every held-out R² is negative, no BMP protocol is implemented, no measurement exists, and real-digester transfer is documented to fail (C-007). A higher number would be a defect, not a strength |

**Weakest-claim autopsy.** The weakest load-bearing claim is: *"the simulator's structure, its factors,
shapes and thresholds, is an adequate representation of food-waste anaerobic digestion."* Evidence against,
from this project's own outputs:

- its calibration anchors do not all reproduce from its own equations (five of thirteen move by 6–74
  mL/g VS; C-009);
- the largest single structural effect in the sweep is a **direction the literature disputes** (the TS
  form; −65.2 % median yield, −32.1 % on the recommendation; C-005);
- a documented class of real effect, pre-treatment acting on *rate* rather than ultimate potential
  (C-004), **cannot appear** in a single endpoint yield with no rate descriptor;
- one delivered variable, the inoculum-to-substrate ratio, is a declared no-op (C-011), so models will
  show ≈ zero importance for it regardless of the real world;
- every model fails out of distribution, and the in-distribution winner's importance is dominated by a
  *derived* column (`ph_measured`), the models lean on the simulator's acidification channel;
- the unit is a declared scale adoption from a methods source, with **no BMP protocol implemented**.

**Verdict on the autopsy: the claim is NOT SUPPORTED, and the project does not rest on it.** Every
conclusion in `report.md` is scoped to the simulator, the held-out failure is published as the
extrapolation limit, and the optimiser's recipe is reported as an artefact. What would raise this claim's
standing is exactly what the project cannot do alone: the tier-B evidence synthesis and the tier-C
supervised measurement described in report §11.

## §8: posteriors at the end of the project

| Prior | Pre-evidence | End of project | Basis |
|---|---|---|---|
| P-A *A. oryzae* benefit is real for food waste | 0.30 | **0.40 (untested)** | No exact-hypothesis study exists (C-003 `partial`); the simulation cannot test it, its factor moves the level ±8–10 % and the recommendation 0.0 % |
| P-B lipid/LCFA inhibition has a threshold | 0.75 | **0.85** | C-002 supported; the LCFA channel moves the recommendation (−17.1 % at η = 0.030) |
| P-C synthetic ranking informs real ranking | 0.15 | **0.10** | All held-out R² negative; transfer failure documented (C-007) |
| P-D recommendation survives ±5 % perturbation | 0.55 | **0.10** | F5 fired on the oracle in both tiers (26 % / 32 % feasible) |

The largest movement went **against** the project's most attractive claim, which is the direction the
steelman rule was written to protect. The prior movements in full are listed in section 8.

## §9: the audit's own limits

1. This audit is **not independent**: the same person built the artefacts and audited them. External review
   is the obvious next control, and the reproduction recipe in report §10 exists to make it cheap.
2. Part A's 14 items are **derived**, not the brief's verbatim list (§0).
3. "PASS" here means the process/software claim held; it is not evidence about digesters (§0 banner).
4. The audit leaned on the guard for artefact-level checks and on commands for numbers; prose remains
   checked only by discipline, which is why item #3 is PARTIAL and why the rule is written down rather than
   asserted.
