"""Wave F: the automated content guard.

Two standing rules have to hold for every artefact this project publishes:

1. **Computational only** (requirement R15). Nothing in `report.md`, `results/` or the committed
   datasets may read as instructions for culturing organisms, building or pressurising vessels,
   handling gas, or operating a digester. The guard is a denylist of phrasings that would only
   appear in such instructions.
2. **Labelled SIMULATED** (requirements R9, R26). Every results CSV row carries the marker, every
   results JSON says `simulated: true`, and the simulator version travels with the numbers.

The guard is itself tested: a planted violation must be caught, so a passing guard means the
check ran rather than that it found nothing to look at.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import pytest

from src import config

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT = REPO_ROOT / "report.md"
RESULTS = config.RESULTS_DIR

#: Phrasings that belong to operational instructions. Each entry is (pattern, why it is banned).
DENYLIST: tuple[tuple[str, str], ...] = (
    (r"\bhow to (build|construct|assemble|operate|run|start|seal|pressuri[sz]e)", "build/operate instructions"),
    (r"\bstep[- ]by[- ]step\b", "step-by-step procedure"),
    (r"\b(instructions?|directions?) (for|to) (building|assembling|culturing|operating|starting)", "instructional framing"),
    (r"\b(culture|culturing|inoculate|streak|incubate|autoclave|sterili[sz]e|agar|petri|spore suspension)\b", "microbiology procedure"),
    (r"\b(pressuri[sz]e|pressure[- ]test|seal the (vessel|container|drum|reactor)|gas[- ]?tight|leak[- ]test)\b", "vessel/pressure procedure"),
    (r"\b(connect|attach|route) (the )?(gas|hose|tubing|burner|stove|flame)", "gas-handling instruction"),
    (r"\b(open flame|ignite|light the|burner tip|flame arrestor)\b", "flammable-gas handling"),
    (r"\b(you should (build|assemble|culture|inoculate|pressuri[sz]e))\b", "second-person instruction"),
    (r"\b(materials? (list|needed)|tools? (list|needed)|bill of materials)\b", "build list"),
)

#: Required labels, checked on every artefact that carries numbers.
SIMULATED_MARKER = config.SIMULATED_MARKER


def _scan(text: str) -> list[str]:
    """Return the denylist reasons that fired, with the matched text."""
    hits: list[str] = []
    for pattern, why in DENYLIST:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            hits.append(f"{why}: '{match.group(0)}'")
    return hits


def _text_targets() -> list[Path]:
    targets: list[Path] = []
    if REPORT.exists():
        targets.append(REPORT)
    for pattern in ("*.md", "*.csv", "*.json"):
        targets.extend(sorted(path for path in RESULTS.rglob(pattern) if path.is_file()))
    targets.extend(sorted(config.DATA_DIR.glob("*.csv")))
    targets.extend(sorted(config.DATA_DIR.glob("*.json")))
    return targets


# --------------------------------------------------------------------------- the guard itself
@pytest.mark.parametrize(
    "sample",
    [
        "Step-by-step: how to build the digester from a drum.",
        "Culture the fungus on agar and then inoculate the substrate.",
        "Seal the vessel and pressure-test it before connecting the gas hose.",
        "You should culture Aspergillus oryzae for five days.",
        "Materials list: drum, hose, valve.",
    ],
)
def test_the_guard_catches_planted_violations(sample: str) -> None:
    assert _scan(sample), f"the guard did not flag {sample!r}"


@pytest.mark.parametrize(
    "sample",
    [
        "The simulation treats pre-treatment as a hypothesis to test, not a guaranteed effect.",
        "No experiment was performed, no reactor was built, and no organism was cultured here.",
        "This study is computational: it generates synthetic data and fits regression models.",
    ],
)
def test_the_guard_does_not_fire_on_the_project_s_own_language(sample: str) -> None:
    assert _scan(sample) == [], f"the guard fired on legitimate text {sample!r}"


# --------------------------------------------------------------------------- published artefacts
def test_there_is_something_to_guard() -> None:
    """A guard with no targets is a guard that always passes, so the target set is asserted."""
    targets = _text_targets()
    assert targets, "the guard found no artefact to scan"
    assert any(path.parent == config.DATA_DIR for path in targets), "the dataset is not covered"
    # `results/` and `report.md` join this set automatically as soon as they exist (Phase 4/5)


def test_the_guard_runs_against_a_freshly_produced_artefact_set(tmp_path: Path) -> None:
    """Generate the pipeline's own outputs now and scan them: the check is never vacuous."""
    import subprocess
    import sys

    def run(module: str, args: list[str]) -> None:
        done = subprocess.run(
            [sys.executable, "-m", module, *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
        assert done.returncode == 0, done.stderr

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    run("src.simulate_data", ["--seed", "11", "--n-scenarios", "12", "--ood", "--outdir", str(data_dir)])
    run("src.evaluate", ["--seeds", "11", "--n-scenarios", "20", "--ood-scenarios", "0",
                         "--outdir", str(tmp_path / "results")])
    run("src.optimize", ["--seed", "11", "--n-scenarios", "20", "--models", "dummy",
                         "--perturbation-draws", "5", "--max-iterations", "5",
                         "--population-size", "4", "--outdir", str(tmp_path / "optimisation")])

    produced = sorted(path for path in tmp_path.rglob("*") if path.is_file())
    assert produced, "the pipeline produced nothing to scan"
    offenders = [f"{path.name} -> {hit}" for path in produced
                 for hit in _scan(path.read_text(encoding="utf-8", errors="replace"))]
    assert not offenders, "operational content found in fresh pipeline output:\n" + "\n".join(offenders)


def test_no_published_artefact_reads_as_an_operating_instruction() -> None:
    offenders: list[str] = []
    for path in _text_targets():
        hits = _scan(path.read_text(encoding="utf-8", errors="replace"))
        offenders.extend(f"{path.relative_to(REPO_ROOT)} -> {hit}" for hit in hits)
    assert not offenders, "operational content found:\n" + "\n".join(offenders)


def test_every_results_csv_row_is_labelled_simulated() -> None:
    for path in sorted(RESULTS.rglob("*.csv")):
        frame = pd.read_csv(path)
        assert "simulated" in frame.columns, path
        assert (frame["simulated"] == SIMULATED_MARKER).all(), path
        assert "simulator_version" in frame.columns, path
        assert (frame["simulator_version"] == config.SIMULATOR_VERSION).all(), path


def test_every_results_json_declares_its_provenance() -> None:
    for path in sorted(RESULTS.rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and payload.get("simulated") is True:
            assert payload.get("data_provenance") == config.DATA_PROVENANCE, path
            assert payload.get("simulator_version") == config.SIMULATOR_VERSION, path
        else:
            pytest.fail(f"{path} does not declare simulated provenance")


def test_every_committed_dataset_row_is_labelled_simulated() -> None:
    for path in sorted(config.DATA_DIR.glob("*.csv")):
        frame = pd.read_csv(path)
        assert "data_provenance" in frame.columns, path
        assert (frame["data_provenance"] == config.DATA_PROVENANCE).all(), path
        assert (frame["simulator_version"] == config.SIMULATOR_VERSION).all(), path


def test_the_report_when_it_exists_carries_the_simulated_scope() -> None:
    if not REPORT.exists():
        pytest.skip("report.md is written in Phase 5; the guard covers it then")
    text = REPORT.read_text(encoding="utf-8")
    assert SIMULATED_MARKER in text.upper()
    assert "synthetic" in text.lower()
