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

- **GitHub Actions ran for the first time on 2026-10-08** and failed twice, both times on something that
  only exists on a clean runner: a bare `pytest` could not import `src` (fixed with a `pythonpath` entry
  in `pyproject.toml`), and on Python 3.12 `mypy` rejected the `np.maximum.reduce([...])` call in
  `src/simulate_data.py` because the numpy 2.5 stubs type it differently (rewritten as a nested
  `np.maximum`, checked against both the 2.4 and the 2.5 stub sets). The runs after those two fixes had
  not happened when this was written.
- **Mutation testing was done by hand.** Four mutants in the final wave, four killed, each with its observed
  failure counts. No mutation tool was available, and none is claimed.
- **Nothing was pushed by the assistant.** The delivery was a files-only archive with no history, and the
  author uploaded it to `github.com/SarvanshRaj/biogas-optimization-research` himself. The commits on
  `main` from 2026-10-08 onward are his.
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

What did not change: every number, every citation, every `SIMULATED` label, and the gate outcomes. The
AI-assistance paragraphs that the report and the README carried at the time were later removed by the
author; that edit and the others that followed this trim are recorded below.

## Hashes of the plan documents

Recorded on 2026-10-07, after the trim. Where a document was edited for wording or paths, the prefix from
before the edit is shown for comparison. Two of these documents were edited again on 2026-10-08; their
current prefixes are at the end of this file.

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

## Edits after the trim, 2026-10-08

A second pass over the same files, made after the repository was uploaded to GitHub. Nothing in it touches
a research question, a falsifier, a threshold or a decision rule.

- The paragraphs that disclosed AI assistance in `README.md` and `report.md` were removed by the author.
  `docs/requirements_traceability.md` therefore records R24 as **not met**, which is the honest status for
  a requirement whose delivered item no longer exists.
- `docs/preregistration.md` named a working branch that no longer exists and pointed at a lock record the
  trim had deleted. Both now describe what survives.
- The same file carried a leftover placeholder label, and `docs/sources.json` named the citation rule by
  that same label. Neither meant anything outside the planning notes, so both now state the rule itself.
- `report.md` and `docs/test_matrix.md` sent readers to `docs/notebook/test_log.md`, which the trim
  deleted. They now point at `tests/test_simulate_data.py` and `docs/tdd_log.md`.
- `docs/tdd_log.md` said the dash helper was kept rather than deleted. It was deleted; the sentence and
  the tree now agree.
- The claim that `.github/workflows/ci.yml` had never run was true when written and false from 2026-10-08,
  when the workflow first executed on GitHub and failed twice: a bare `pytest` could not import `src`,
  and on Python 3.12 `mypy` rejected a `np.maximum.reduce([...])` call that the numpy 2.5 stubs type more
  strictly. Both are fixed in the tree, with `pythonpath` in `pyproject.toml` and a nested `np.maximum` in
  `src/simulate_data.py`. The runs that follow the fixes had not happened when this was written.
- The same false claim appeared in six places (`README.md`, the workflow header, `docs/notebook.md`,
  `docs/phase6_audit.md` twice, `docs/tdd_log.md`, and `report.md` §10); all six now say what happened.

Hashes after the 8 October edits:

| Document | SHA-256 prefix now | On 2026-10-07 |
|---|---|---|
| `docs/preregistration.md` | `04e8ec9daaff3f77` | `1a2085cc05219063` |
| `docs/test_matrix.md` | `523a4e00499f3bb9` | `60596e05baa98024` |

The other four plan documents are byte-identical to their 7 October state, so their recorded prefixes
(`e8e4b998ebaecbe5`, `17e5d083bea7d09f`, `b8ba33b0df333ff8`, `686a0d5921190c85`) did not move.

Those frozen documents still name files that the trim removed (`docs/child_prompt_template.md`, the
`docs/notebook/` tree). That is deliberate: they record what the lock created and what the
pre-registration instructed at the time, and editing them would invalidate the hashes they are pinned by.
The mapping from the removed files to what replaced them is in the trim section above.
