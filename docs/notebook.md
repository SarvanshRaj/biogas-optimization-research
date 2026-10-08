# Notes on how this was built

A running record, kept for whoever reads the repository later. Nothing here is needed to run the study;
the commands are in `results/README.md` and the results are in `report.md`.

## What was here at the start

A shallow clone of `github.com/SarvanshRaj/biogas-optimization-research` at commit `4c3c9cf`, with
`README.md` as the only tracked file. The README described the 2025 Sakura Science Exchange Programme
concept, a mechanical fermentation prototype which had been cleared for elimination and not selected. That
programme ended before any software stage, so this repository did not continue it, and no data from it
appears anywhere here.

## The phases, and what each one produced

| Phase | Work | Artefacts still in the repository |
|---|---|---|
| 0 | Scope, five research questions, the plan, the falsifiers, the test plan, all written before any code | `docs/preregistration.md`, `docs/preregistration_addendum_01..03.md`, `docs/test_matrix.md` |
| 1 | Evidence pass: 32 sources with locators and a verification status each, plus the parameter table | `docs/literature_review.md`, `docs/parameter_table.md`, `docs/references.md`, `docs/sources.json` |
| 2 | Model notes frozen before code; six critical reviews of the plan | `docs/model_specification.md`, `docs/disconfirmation_reviews.md` |
| 3 | Tests first, then `src/`; six waves of RED before GREEN | `src/`, `tests/`, `docs/tdd_log.md`, `docs/known_issues.md` |
| 4 | Full run at five seeds, the optimiser, the sensitivity sweep, the contradictions review | `data/synthetic/`, `results/`, `docs/contradictions.md` |
| 5 | The write-up and the student explanation | `report.md` |
| 6 | Hard audit: 14 items with verdicts, requirement rows, repository review | `docs/phase6_audit.md`, `docs/requirements_traceability.md` |

## Numbers found to be wrong, and fixed

Five written claims did not survive being re-measured, and each is corrected where it appears:

1. A mutation-testing table whose failure counts had been written from expectation rather than from a run.
   Re-run, and the observed counts recorded in `docs/tdd_log.md`.
2. The file count and total size of `results/`, both mis-stated in the hand-over.
3. Two models' MAE and RMSE in the first draft of `report.md` (Ridge and the random forest).
4. The byte size of the dataset, recorded as 10,003,242 bytes while the committed tree measures 9,999,347.
5. The sentence that every held-out R-squared is negative. It is negative in 24 of the 25 model-seed cells;
   Ridge at seed 59 is positive, and every model's five-seed mean is negative.

The rule that came out of this: a number that appears in a document is copied from a command, never from
memory.

## Things that are blocked, not done

- **GitHub Actions has never run.** The workflow is committed and mirrors the local commands, but the API
  check from this environment returned 403, so CI is added and unverified.
- **Mutation testing was done by hand.** Four mutants in the final wave, four killed, each with its observed
  failure counts. No mutation tool was available, and none is claimed.
- **Nothing was pushed.** The remote `main` is still at `4c3c9cf`. The delivery is a files-only archive.
- **The sandbox restarted twice** during the work, which flattened the local commit history and is why there
  is a labelled recovery commit. The commit identifiers are local to that machine.

## Documentation trim, 2026-10-07

The repository had accumulated working notes that documented the process rather than the study: a per-phase
log, per-test verdict logs, a calibration diary, an access log, a rabbit-hole queue, query logs, a mind map,
an iceberg map, a bibliography file that the reference list had already replaced, and a capability matrix.
None of them was evidence for a result, and several were longer than the report.

Removed (18 files): `docs/child_prompt_template.md`, `docs/notebook.md`'s old phase/law tables, and the
files under `docs/notebook/` other than the three below. Content that carried evidence moved instead of
disappearing:

| Old file | Now |
|---|---|
| `docs/notebook/cite_ledger.json` | `docs/sources.json` |
| `docs/notebook/claim_graph.json` | `docs/claims.json` |
| `docs/notebook/conflict_map.md` | `docs/contradictions.md` |
| `docs/notebook/bib.md` | `docs/references.md` |
| `docs/spec_v1_anchor_recheck.md` | `docs/known_issues.md` |

`docs/` went from 35 files and about 6,200 lines of markdown to 16 markdown files and about 3,100
lines, plus two JSON records (`docs/sources.json`, `docs/claims.json`). The plan
documents were also edited, for wording and file paths only: no research question, falsifier, threshold or
decision rule changed. Their SHA-256 prefixes before and after are recorded at the end of this file.

Also removed: a helper script used during the readability pass, `tools/humanize_dashes.py`, which replaced
long dashes with commas and colons in the prose. Its report is reproduced in the note below, and the script
itself was not part of the study.

## Readability pass, 2026-10-07

The prose had one habit that made it read as machine-written: long dashes used where a comma, a colon or a
full stop belongs. A first pass replaced 607 of them across 27 files, leaving the six plan documents aside
because their text is quoted in tests and in the results. Those six were edited anyway when the notebook
files were removed, so the 91 long dashes in them were replaced in that pass, along with 8 in the data
dictionary. No long dash remains anywhere in the repository outside code spans and quoted text.

Two places were left alone on purpose: the strings in `src/sensitivity.py` that are baked into
`results/sensitivity/sensitivity_metadata.json`, since editing them would put the code and the artefact out
of step, and the vocabulary `SIMULATED`, which appears on every artefact and is not stylistic.

What did not change: every number, every citation, every `SIMULATED` label, the gate outcomes, and the
statement that this work was built with AI assistance.

## Hashes of the plan documents

Recorded on 2026-10-07, after the trim. Where a document was edited for wording or paths, the prefix from
before the edit is shown for comparison.

| Document | SHA-256 prefix now | Before the edit |
|---|---|---|
| `docs/preregistration.md` | `1a2085cc05219063` | `8d3666e8` |
| `docs/preregistration_addendum_01.md` | `e8e4b998ebaecbe5` | `8984b1fd` |
| `docs/preregistration_addendum_02.md` | `17e5d083bea7d09f` | `f56eff06` |
| `docs/preregistration_addendum_03.md` | `b8ba33b0df333ff8` | `0b13c0ac` |
| `docs/model_specification.md` | `686a0d5921190c85` | `8b02c21d` |
| `docs/test_matrix.md` | `60596e05baa98024` | `daf48788` |

The archive is built straight from the delivery commit, so its entry count and size are stated in the
hand-over message rather than here: a file cannot report the size of the archive that contains it.
