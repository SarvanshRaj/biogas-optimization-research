"""CLI contract tests (test matrix group D-CLI): arguments, files written, error paths."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src import config
from src.simulate_data import main


def test_cli_writes_one_seed_and_reports_simulated(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["--seed", "11", "--n-scenarios", "20", "--outdir", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "SIMULATED" in out
    frame_path = tmp_path / "foodwaste_biogas_seed11.csv"
    assert frame_path.exists()
    assert (tmp_path / "latent_factors_seed11.csv").exists()
    frame = pd.read_csv(frame_path)
    assert len(frame) == 20 * config.N_REPLICATES
    meta = json.loads((tmp_path / "metadata_seed11.json").read_text(encoding="utf-8"))
    assert meta["data_provenance"] == "synthetic"
    assert meta["simulator_version"] == config.SIMULATOR_VERSION
    assert "SIMULATED" in meta["scale_adoption_note"].upper()
    assert "bmp" in meta["bmp_protocol"].lower()


def test_cli_all_seeds_and_ood(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["--all-seeds", "--n-scenarios", "12", "--ood", "--outdir", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    for seed in config.SEEDS:
        assert (tmp_path / f"foodwaste_biogas_seed{seed}.csv").exists()
        assert (tmp_path / f"latent_factors_seed{seed}.csv").exists()
        assert (tmp_path / f"foodwaste_biogas_ood_seed{seed}.csv").exists()
    assert out.count("held-out OOD") == len(config.SEEDS)


def test_cli_default_outdir_is_the_project_data_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    import importlib

    module = importlib.import_module("src.simulate_data")
    monkeypatch.setattr(module.config, "DATA_DIR", tmp_path)
    rc = module.main(["--seed", "11", "--n-scenarios", "6"])
    assert rc == 0
    assert (tmp_path / "foodwaste_biogas_seed11.csv").exists()


def test_cli_rejects_non_positive_scenario_count(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        main(["--n-scenarios", "0", "--outdir", str(tmp_path)])


def test_cli_unknown_argument_is_an_error() -> None:
    with pytest.raises(SystemExit):
        main(["--not-a-flag"])


def test_cli_help_exits_zero() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0


def test_cli_stops_when_validation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib

    module = importlib.import_module("src.simulate_data")
    monkeypatch.setattr(
        module, "validate_frame", lambda frame: {"ok": False, "checks_failed": ["injected"]}
    )
    with pytest.raises(SystemExit) as excinfo:
        module.main(["--seed", "11", "--n-scenarios", "6", "--outdir", str(tmp_path)])
    assert "validation failed" in str(excinfo.value)


def test_written_csv_is_reloadable_and_labelled(tmp_path: Path) -> None:
    main(["--seed", "23", "--n-scenarios", "8", "--outdir", str(tmp_path)])
    frame = pd.read_csv(tmp_path / "foodwaste_biogas_seed23.csv")
    assert list(frame.columns) == list(config.FRAME_COLUMNS)
    assert (frame["data_provenance"] == "synthetic").all()
    assert frame["as_of"].nunique() == 1

def test_cli_stops_when_held_out_validation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib

    module = importlib.import_module("src.simulate_data")
    monkeypatch.setattr(
        module,
        "simulate_ood",
        lambda seed, n_scenarios=None, _pool_factor=1.6: module.simulate(
            seed=seed, n_scenarios=5
        )[0],
    )
    with pytest.raises(SystemExit) as excinfo:
        module.main(["--seed", "11", "--n-scenarios", "6", "--ood", "--outdir", str(tmp_path)])
    assert "held-out validation failed" in str(excinfo.value)
