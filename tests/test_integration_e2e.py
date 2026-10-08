"""Wave E: the end-to-end integration test.

Every other test file checks one module. This one checks the **seams** between them - that the
column contract survives from the simulator to the optimiser, that the CLIs chain, that the
committed dataset in `data/synthetic/` is exactly what the generator produces today, and that a
reviewer can re-derive the chain in a fresh directory.

It deliberately uses small sizes (a few hundred rows) so it can run on every commit; the size that
the study reports is Phase 4's, not this file's.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import pytest

from src import config

matplotlib.use("Agg")

REPO_ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------- seams
def test_the_column_contract_survives_from_simulator_to_optimiser(small_frame: pd.DataFrame) -> None:
    from src.optimize import candidate_frame, true_objective
    from src.simulate_data import validate_frame
    from src.train_models import make_feature_frame

    # the simulator's target is declared once and used by everyone
    assert config.TARGET in config.OUTPUT_COLUMNS
    assert config.TARGET in small_frame.columns
    assert (small_frame[config.TARGET] >= 0).all()
    assert validate_frame(small_frame)["ok"] is True

    # a candidate built by the optimiser has the same feature columns the model was trained on
    candidate = {
        **config.BASELINE_PROCESS,
        "carb_fraction": 0.70,
        "protein_fraction": 0.10,
        "total_solids_pct": 12.0,
        "temperature_c": 35.0,
        "ph_setpoint": 7.0,
        "olr_kg_vs_m3_d": 1.5,
        "hrt_days": 30.0,
    }
    frame = candidate_frame(candidate)
    assert set(make_feature_frame(frame).columns) == set(config.FEATURES)
    assert np.isfinite(true_objective(candidate))


def test_the_evaluation_metrics_are_the_training_metrics() -> None:
    from src.evaluate import evaluate_seed
    from src.train_models import regression_metrics

    y_true = np.array([1.0, 2.0, 3.0, 4.0])
    y_pred = np.array([1.5, 2.5, 2.5, 4.0])
    # residuals  -0.5, -0.5, +0.5, 0.0
    #   MAE  = 1.5 / 4 = 0.375
    #   RMSE = sqrt(0.75 / 4) = 0.4330
    #   R2   = 1 - SS_res / SS_tot = 1 - 0.75 / 5 = 0.85
    assert regression_metrics(y_true, y_pred) == {
        "r2": pytest.approx(0.85),
        "mae": pytest.approx(0.375),
        "rmse": pytest.approx(0.4330127018922193),
        "n": 4,
        "target_std": pytest.approx(y_true.std()),
    }
    # the evaluation pipeline reports exactly those keys, per seed, per model
    result = evaluate_seed(11, 20, ood_scenarios=0, names=("dummy",))
    assert set(result["rows"][0]) >= set(regression_metrics(y_true, y_pred))


def test_a_full_chain_run_in_a_fresh_directory(tmp_path: Path) -> None:
    """generate -> validate -> split -> fit -> evaluate -> optimise, all in one place."""
    from src.evaluate import evaluate_models, write_results
    from src.optimize import run_optimisation, write_optimiser_results
    from src.simulate_data import simulate, validate_frame, write_dataset
    from src.train_models import fit_all_models, save_model, split_frame

    frame, latent = simulate(seed=11, n_scenarios=30)
    assert validate_frame(frame)["ok"] is True

    data_dir = tmp_path / "data"
    written = write_dataset(frame, latent, data_dir, seed=11)
    reloaded = pd.read_csv(written["frame"])
    assert len(reloaded) == len(frame)
    assert (reloaded["data_provenance"] == config.DATA_PROVENANCE).all()
    assert (reloaded["simulator_version"] == config.SIMULATOR_VERSION).all()

    splits = split_frame(reloaded)
    fitted = fit_all_models(splits, 11, names=("dummy", "ridge"))
    assert set(fitted) == {"dummy", "ridge"}
    for model in fitted.values():
        path = save_model(model, tmp_path / "models")
        meta = json.loads((path.parent / f"{path.stem}.json").read_text(encoding="utf-8"))
        assert meta["simulated"] is True and meta["simulator_version"] == config.SIMULATOR_VERSION

    evaluation = evaluate_models(seeds=(11,), n_scenarios=30, ood_scenarios=6, names=("dummy", "ridge"))
    eval_paths = write_results(evaluation, tmp_path / "results")
    assert all(path.exists() for path in eval_paths.values())
    assert evaluation["rules"]["f3_rule"] and evaluation["rules"]["f7_rule"]

    optimisation = run_optimisation(
        seed=11,
        n_scenarios=30,
        model_names=("dummy", "ridge"),
        tiers=("C1",),
        perturbation_draws=10,
        max_iterations=8,
        population_size=5,
    )
    opt_paths = write_optimiser_results(optimisation, tmp_path / "optimisation")
    assert all(path.exists() for path in opt_paths.values())
    tier = optimisation["tiers"]["C1"]
    assert tier["checks"]["oracle_beats_reference"] is True
    assert tier["arms"]["true"]["constraints"]["feasible"] is True


def test_the_chain_is_deterministic_end_to_end(tmp_path: Path) -> None:
    from src.evaluate import evaluate_models
    from src.optimize import run_optimisation

    def chain() -> tuple[list[dict], float]:
        evaluation = evaluate_models(seeds=(11,), n_scenarios=30, ood_scenarios=6, names=("dummy", "ridge"))
        optimisation = run_optimisation(
            seed=11,
            n_scenarios=30,
            model_names=("dummy", "ridge"),
            tiers=("C1",),
            perturbation_draws=10,
            max_iterations=8,
            population_size=5,
        )
        return evaluation["rows"], optimisation["tiers"]["C1"]["arms"]["true"]["true_yield"]

    assert chain() == chain()


def test_the_test_split_is_untouched_until_the_end(small_frame: pd.DataFrame) -> None:
    from src.evaluate import evaluate_seed

    result = evaluate_seed(11, 30, ood_scenarios=0, names=("dummy", "ridge"))
    splits = result["splits"]
    for model in result["fitted"].values():
        assert model.fit_rows == len(splits["train"]) + len(splits["validation"])
    test_rows = [row for row in result["rows"] if row["split"] == "test"]
    assert len(test_rows) == 2  # exactly one row per model, produced once
    assert all("test" not in json.dumps(model.tuning_log).lower() for model in result["fitted"].values())


# --------------------------------------------------------------------------- the committed dataset
@pytest.fixture(scope="module")
def committed_dataset() -> dict[int, pd.DataFrame]:
    frames: dict[int, pd.DataFrame] = {}
    for seed in config.SEEDS:
        path = config.DATA_DIR / f"foodwaste_biogas_seed{seed}.csv"
        if not path.exists():
            continue
        frames[seed] = pd.read_csv(path)
    return frames


def test_the_committed_dataset_exists_for_every_declared_seed() -> None:
    missing = [
        seed
        for seed in config.SEEDS
        if not (config.DATA_DIR / f"foodwaste_biogas_seed{seed}.csv").exists()
    ]
    assert not missing, (
        f"the committed dataset is missing seeds {missing}; regenerate it with "
        "`python3 -m src.simulate_data --all-seeds --ood --outdir data/synthetic`"
    )


def test_the_committed_dataset_is_what_the_generator_produces_today(
    committed_dataset: dict[int, pd.DataFrame],
) -> None:
    """If the simulator is ever edited, this fails before anyone reports a stale number."""
    from src.simulate_data import simulate

    for seed, committed in committed_dataset.items():
        fresh, _ = simulate(seed=seed, n_scenarios=config.N_SCENARIOS)
        assert list(committed.columns) == list(fresh.columns), seed
        assert len(committed) == len(fresh), seed
        for column in fresh.columns:
            if pd.api.types.is_numeric_dtype(fresh[column]):
                np.testing.assert_allclose(
                    committed[column].to_numpy(dtype=float),
                    fresh[column].to_numpy(dtype=float),
                    rtol=1e-9,
                    atol=1e-9,
                    err_msg=f"seed {seed}, column {column}",
                )
            else:
                pd.testing.assert_series_equal(
                    committed[column], fresh[column], check_names=False, obj=f"seed {seed}"
                )


def test_the_committed_dataset_validates(committed_dataset: dict[int, pd.DataFrame]) -> None:
    from src.simulate_data import validate_frame

    for seed, frame in committed_dataset.items():
        report = validate_frame(frame)
        assert report["ok"] is True, (seed, report["checks_failed"])
        assert (frame["data_provenance"] == config.DATA_PROVENANCE).all(), seed
        assert (frame["simulator_version"] == config.SIMULATOR_VERSION).all(), seed


def test_the_held_out_files_are_outside_the_training_envelope() -> None:
    from src.simulate_data import validate_frame

    for seed in config.SEEDS:
        path = config.DATA_DIR / f"foodwaste_biogas_ood_seed{seed}.csv"
        assert path.exists(), path
        frame = pd.read_csv(path)
        report = validate_frame(frame, ranges=config.OOD_RANGES)
        assert report["ok"] is True, (seed, report["checks_failed"])
        assert (frame["lipid_fraction"] > config.INPUT_RANGES["lipid_fraction"][1]).all(), seed


# --------------------------------------------------------------------------- the CLIs chain
def _run(module: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )


def test_the_five_clis_chain_into_one_pipeline(tmp_path: Path) -> None:
    started = time.time()
    data_dir = tmp_path / "data" / "synthetic"
    data_dir.mkdir(parents=True)

    simulate_run = _run(
        "src.simulate_data",
        ["--seed", "11", "--n-scenarios", "20", "--ood", "--outdir", str(data_dir)],
    )
    assert simulate_run.returncode == 0, simulate_run.stderr
    assert "[SIMULATED]" in simulate_run.stdout
    assert (data_dir / "foodwaste_biogas_seed11.csv").exists()

    train_run = _run(
        "src.train_models", ["--seed", "11", "--n-scenarios", "20", "--outdir", str(tmp_path / "models")]
    )
    assert train_run.returncode == 0, train_run.stderr
    assert train_run.stdout.count("[SIMULATED]") == len(config.MODEL_NAMES)

    eval_run = _run(
        "src.evaluate",
        [
            "--seeds", "11",
            "--n-scenarios", "20",
            "--ood-scenarios", "0",
            "--outdir", str(tmp_path / "results"),
        ],
    )
    assert eval_run.returncode == 0, eval_run.stderr
    assert "[SIMULATED]" in eval_run.stdout

    opt_run = _run(
        "src.optimize",
        [
            "--seed", "11",
            "--n-scenarios", "20",
            "--models", "dummy",
            "--perturbation-draws", "5",
            "--max-iterations", "5",
            "--population-size", "4",
            "--outdir", str(tmp_path / "optimisation"),
        ],
    )
    assert opt_run.returncode == 0, opt_run.stderr
    assert "not a real recipe" in opt_run.stdout

    sweep_run = _run(
        "src.sensitivity",
        [
            "--seed",
            "11",
            "--n-scenarios",
            "12",
            "--models",
            "ridge",
            "--assumptions",
            "ts_shape",
            "--max-iterations",
            "4",
            "--population-size",
            "3",
            "--perturbation-draws",
            "3",
            "--outdir",
            str(tmp_path / "sensitivity"),
        ],
    )
    assert sweep_run.returncode == 0, sweep_run.stderr
    assert sweep_run.stdout.count("[SIMULATED]") >= 3  # one line per swept level
    assert (tmp_path / "sensitivity" / "sensitivity_sweep.csv").exists()

    for module, stdout in (
        ("simulate_data", simulate_run.stdout),
        ("train_models", train_run.stdout),
        ("evaluate", eval_run.stdout),
        ("optimize", opt_run.stdout),
        ("sensitivity", sweep_run.stdout),
    ):
        assert "traceback" not in stdout.lower(), module

    assert time.time() - started < 900


def test_no_cli_writes_outside_its_outdir(tmp_path: Path) -> None:
    """A pipeline that scribbles into the repository is not reproducible."""
    before = {path: path.stat().st_mtime for path in (REPO_ROOT / "results").rglob("*") if path.is_file()} \
        if (REPO_ROOT / "results").exists() else {}
    outdir = tmp_path / "isolated"
    run = _run(
        "src.optimize",
        [
            "--seed", "11",
            "--n-scenarios", "20",
            "--models", "dummy",
            "--perturbation-draws", "5",
            "--max-iterations", "5",
            "--population-size", "4",
            "--outdir", str(outdir),
        ],
    )
    assert run.returncode == 0, run.stderr
    assert outdir.exists()
    after = {path: path.stat().st_mtime for path in (REPO_ROOT / "results").rglob("*") if path.is_file()} \
        if (REPO_ROOT / "results").exists() else {}
    assert before == after, "a CLI run touched results/ even though --outdir pointed elsewhere"
