"""The five models: fitting, tuning, persistence, determinism and edge cases (D-MOD, D-PRE, D-CTL)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from src import config
from src.simulate_data import simulate


@pytest.fixture(scope="module")
def splits() -> dict[str, pd.DataFrame]:
    from src.train_models import split_frame

    return split_frame(simulate(seed=11, n_scenarios=70)[0])


@pytest.fixture(scope="module")
def fitted(splits: dict[str, pd.DataFrame]) -> dict[str, Any]:
    from src.train_models import fit_all_models

    return fit_all_models(splits, seed=11)


# --------------------------------------------------------------------------- model set
def test_exactly_the_five_declared_models_are_fitted(fitted: dict) -> None:
    assert set(fitted) == set(config.MODEL_NAMES)
    assert len(fitted) == 5


def test_no_extra_model_can_be_requested(splits: dict[str, pd.DataFrame]) -> None:
    from src.train_models import fit_all_models

    with pytest.raises(ValueError, match="unknown model"):
        fit_all_models(splits, seed=11, names=("xgboost",))


def test_every_model_is_a_documented_estimator(fitted: dict) -> None:
    from sklearn.dummy import DummyRegressor
    from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
    from sklearn.linear_model import Ridge
    from sklearn.neural_network import MLPRegressor

    expected = {
        "dummy": DummyRegressor,
        "ridge": Ridge,
        "random_forest": RandomForestRegressor,
        "hist_gradient_boosting": HistGradientBoostingRegressor,
        "mlp": MLPRegressor,
    }
    for name, expected_type in expected.items():
        assert isinstance(fitted[name].estimator, expected_type), name


# --------------------------------------------------------------------------- fitting and prediction
def test_all_models_predict_finite_values(splits: dict[str, pd.DataFrame], fitted: dict) -> None:
    from src.train_models import make_feature_frame, predict_model

    features = make_feature_frame(splits["test"])
    target = splits["test"][config.TARGET]
    for name, model in fitted.items():
        predictions = predict_model(model, features)
        assert predictions.shape == (len(features),), name
        assert np.isfinite(predictions).all(), name
        # Regression models are not required to respect the simulator's physical bounds, and
        # clipping them would hide model error. The test therefore only forbids wild excursions
        # (observed minima are reported in docs/tdd_log.md).
        assert predictions.min() > target.min() - 100.0, name
        assert predictions.max() < target.max() + 100.0, name


def test_dummy_baseline_has_no_skill_on_the_test_split(
    splits: dict[str, pd.DataFrame], fitted: dict
) -> None:
    from sklearn.metrics import r2_score

    from src.train_models import make_feature_frame, predict_model

    features = make_feature_frame(splits["test"])
    predictions = predict_model(fitted["dummy"], features)
    r2 = r2_score(splits["test"][config.TARGET], predictions)
    assert -0.05 < r2 < 0.05, r2


def test_tuned_models_beat_the_dummy_baseline(splits: dict[str, pd.DataFrame], fitted: dict) -> None:
    from sklearn.metrics import r2_score

    from src.train_models import make_feature_frame, predict_model

    features = make_feature_frame(splits["test"])
    targets = splits["test"][config.TARGET]
    scores = {name: r2_score(targets, predict_model(m, features)) for name, m in fitted.items()}
    best = max(s for n, s in scores.items() if n != "dummy")
    assert best > scores["dummy"] + 0.2, scores


# --------------------------------------------------------------------------- tuning protocol
def test_chosen_parameters_come_from_the_declared_grid(fitted: dict) -> None:
    for name, model in fitted.items():
        assert model.params in config.MODEL_GRIDS[name], name


def test_tuning_log_never_mentions_the_test_split(fitted: dict) -> None:
    for name, model in fitted.items():
        assert model.tuning_log, name
        for entry in model.tuning_log:
            keys = set(entry)
            assert {"train_r2", "validation_r2"} <= keys, (name, keys)
            assert not any("test" in key for key in keys), (name, keys)


def test_test_split_is_never_used_for_selection(splits: dict[str, pd.DataFrame]) -> None:
    """Mutation test: corrupting the test split must not change any fitted model."""
    from src.train_models import fit_all_models, make_feature_frame, predict_model

    clean = fit_all_models(splits, seed=11)
    poisoned = {k: v.copy() for k, v in splits.items()}
    poisoned["test"][config.TARGET] = np.random.default_rng(0).normal(
        poisoned["test"][config.TARGET].mean(), 50.0, len(poisoned["test"])
    )
    dirty = fit_all_models(poisoned, seed=11)

    features = make_feature_frame(splits["test"])
    for name in config.MODEL_NAMES:
        assert clean[name].params == dirty[name].params, name
        np.testing.assert_allclose(
            predict_model(clean[name], features), predict_model(dirty[name], features), rtol=1e-12
        )


def test_tuning_refits_on_train_and_validation_only(splits: dict[str, pd.DataFrame]) -> None:
    """The selected configuration is refitted on train+validation; the test split is untouched."""
    from src.train_models import fit_model

    model = fit_model("ridge", splits, seed=11)
    assert model.fit_rows == len(splits["train"]) + len(splits["validation"])
    assert model.fit_rows != len(splits["train"])


def test_tuning_is_deterministic(splits: dict[str, pd.DataFrame]) -> None:
    from src.train_models import fit_model, make_feature_frame, predict_model

    a = fit_model("random_forest", splits, seed=11)
    b = fit_model("random_forest", splits, seed=11)
    features = make_feature_frame(splits["test"])
    np.testing.assert_allclose(predict_model(a, features), predict_model(b, features), rtol=1e-12)


# --------------------------------------------------------------------------- persistence
def test_models_round_trip_through_disk(splits: dict[str, pd.DataFrame], tmp_path: Path) -> None:
    from src.train_models import (
        fit_model,
        load_model,
        make_feature_frame,
        predict_model,
        save_model,
    )

    model = fit_model("ridge", splits, seed=11)
    path = save_model(model, tmp_path)
    assert path.exists()
    restored = load_model(path)
    features = make_feature_frame(splits["test"])
    np.testing.assert_allclose(
        predict_model(model, features), predict_model(restored, features), rtol=1e-12
    )
    assert restored.name == model.name
    assert restored.params == model.params


def test_artifact_metadata_carries_the_simulated_labels(
    splits: dict[str, pd.DataFrame], tmp_path: Path
) -> None:
    """R28: every metric/artifact must say it is synthetic."""
    import json

    from src.train_models import fit_model, save_model

    model = fit_model("dummy", splits, seed=11)
    path = save_model(model, tmp_path)
    meta = json.loads((tmp_path / f"{path.stem}.json").read_text(encoding="utf-8"))
    assert meta["data_provenance"] == "synthetic"
    assert meta["simulator_version"] == config.SIMULATOR_VERSION
    assert "SIMULATED" in json.dumps(meta).upper()
    assert "simulator" in meta["limitation"].lower()
    assert meta["target"] == config.TARGET
    assert meta["features"] == list(config.FEATURES)


def test_loading_a_missing_artifact_raises(tmp_path: Path) -> None:
    from src.train_models import load_model

    with pytest.raises(FileNotFoundError):
        load_model(tmp_path / "nope.joblib")


# --------------------------------------------------------------------------- edge cases
def test_tiny_dataset_can_be_fitted() -> None:
    from src.train_models import fit_all_models, split_frame

    frame, _ = simulate(seed=11, n_scenarios=6)
    splits = split_frame(frame)
    fitted = fit_all_models(splits, seed=11)
    assert len(fitted) == 5
    from src.train_models import make_feature_frame, predict_model

    features = make_feature_frame(splits["test"])
    for name, model in fitted.items():
        predictions = predict_model(model, features)
        assert predictions.shape == (len(features),), name
        assert np.isfinite(predictions).all(), name


def test_duplicated_rows_do_not_break_fitting() -> None:
    from src.train_models import fit_all_models, split_frame

    frame, _ = simulate(seed=11, n_scenarios=20)
    doubled = pd.concat([frame, frame], ignore_index=True)
    splits = split_frame(doubled)
    fitted = fit_all_models(splits, seed=11)
    assert set(fitted) == set(config.MODEL_NAMES)


def test_singular_feature_column_is_handled() -> None:
    """A perfectly collinear pair must not break the pipeline (trees ignore it, Ridge needs help)."""
    from src.train_models import fit_preprocessor, transform_features

    frame = pd.DataFrame({column: np.linspace(0, 1, 40) for column in config.FEATURES})
    frame["protein_fraction"] = 1.0 - frame["carb_fraction"]
    pre = fit_preprocessor(frame)
    transformed = transform_features(pre, frame)
    assert np.isfinite(transformed).all()


def test_metric_helpers_are_hand_checkable() -> None:
    from src.train_models import regression_metrics

    y_true = np.array([1.0, 2.0, 3.0])
    y_pred = np.array([1.0, 2.0, 5.0])
    metrics = regression_metrics(y_true, y_pred)
    assert metrics["mae"] == pytest.approx(2.0 / 3.0)
    assert metrics["rmse"] == pytest.approx(np.sqrt(4.0 / 3.0))
    # SS_res = 0 + 0 + 4 = 4; SS_tot = 1 + 0 + 1 = 2  ->  R² = 1 - 4/2 = -1
    assert metrics["r2"] == pytest.approx(-1.0)
    assert metrics["n"] == 3


def test_undefined_r2_is_reported_as_none_not_zero() -> None:
    """A constant target makes R² undefined; it must not be silently reported as 0."""
    from src.train_models import regression_metrics

    metrics = regression_metrics(np.array([5.0, 5.0, 5.0]), np.array([5.0, 5.0, 4.0]))
    assert metrics["r2"] is None
    assert metrics["mae"] == pytest.approx(1.0 / 3.0)


def test_metrics_reject_mismatched_shapes() -> None:
    from src.train_models import regression_metrics

    with pytest.raises(ValueError):
        regression_metrics(np.array([1.0, 2.0]), np.array([1.0]))

def test_convergence_warnings_are_recorded_not_hidden(fitted: dict, tmp_path: Path) -> None:
    """A model that does not converge must say so in its artifact, not only in a log."""
    import json

    from src.train_models import save_model

    for name, model in fitted.items():
        assert isinstance(model.convergence_warnings, int), name
        path = save_model(model, tmp_path)
        meta = json.loads((tmp_path / f"{path.stem}.json").read_text(encoding="utf-8"))
        assert isinstance(meta["convergence_warnings"], int), name
        if model.convergence_warnings:
            assert "convergencewarning" in meta["training_notes"].lower(), name
        else:
            assert "no convergence warnings" in meta["training_notes"].lower(), name


def test_train_cli_fits_and_writes_all_five(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from src.train_models import main

    rc = main(["--seed", "11", "--n-scenarios", "30", "--outdir", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.count("[SIMULATED]") == len(config.MODEL_NAMES)
    for name in config.MODEL_NAMES:
        assert (tmp_path / f"{name}.joblib").exists()
        assert (tmp_path / f"{name}.json").exists()
    assert "written" not in out.lower()


def test_train_cli_warns_about_cross_split_duplicates(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import importlib
    import json as _json

    module = importlib.import_module("src.train_models")
    monkeypatch.setattr(
        module,
        "cross_split_duplicate_report",
        lambda parts, tolerance=0.0: {
            "n_exact_cross_split": 2,
            "min_cross_split_distance": 0.0,
            "tolerance": tolerance,
            "n_rows": {k: len(v) for k, v in parts.items()},
        },
    )
    rc = module.main(["--seed", "11", "--n-scenarios", "12", "--outdir", str(tmp_path)])
    assert rc == 0
    assert "appear in two splits" in capsys.readouterr().out
    assert _json.loads((tmp_path / "dummy.json").read_text())["simulated"] is True


def test_train_cli_rejects_an_unknown_model(tmp_path: Path) -> None:
    from src.simulate_data import simulate
    from src.train_models import fit_all_models, split_frame

    splits = split_frame(simulate(seed=11, n_scenarios=12)[0])
    with pytest.raises(ValueError, match="unknown model"):
        fit_all_models(splits, seed=11, names=("mlp", "xgboost"))

def test_split_frame_requires_a_split_column() -> None:
    from src.simulate_data import simulate
    from src.train_models import split_frame

    frame, _ = simulate(seed=11, n_scenarios=12)
    with pytest.raises(ValueError, match="no `split` column"):
        split_frame(frame.drop(columns=["split"]))


def test_split_frame_requires_all_three_parts() -> None:
    from src.simulate_data import simulate
    from src.train_models import split_frame

    frame, _ = simulate(seed=11, n_scenarios=30)
    only_train = frame[frame["split"] == "train"]
    with pytest.raises(ValueError, match="train/validation/test"):
        split_frame(only_train)


def test_fit_preprocessor_rejects_a_non_dataframe() -> None:
    from src.train_models import fit_preprocessor

    with pytest.raises(TypeError, match="DataFrame"):
        fit_preprocessor(np.zeros((3, len(config.FEATURES)), dtype=float))  # type: ignore[arg-type]


def test_build_model_rejects_an_unknown_name() -> None:
    from src.train_models import build_model

    with pytest.raises(ValueError, match="unknown model"):
        build_model("xgboost", {}, 11)


def test_tune_model_rejects_an_unknown_name(splits: dict[str, pd.DataFrame]) -> None:
    from src.train_models import tune_model

    with pytest.raises(ValueError, match="unknown model"):
        tune_model("xgboost", splits, 11)

def test_selection_uses_validation_not_training_score(splits: dict[str, pd.DataFrame]) -> None:
    """The chosen configuration must maximise validation R², not training R².

    Regression for a mutant that survived the first wave-B suite: selecting by training score
    changed nothing, because no test pinned the selection rule. On this fixture the two rules
    disagree, which is asserted below so the check cannot become vacuous.
    """
    import json

    from src.train_models import (
        build_model,
        fit_model,
        fit_preprocessor,
        make_feature_frame,
        transform_features,
    )

    pre = fit_preprocessor(make_feature_frame(splits["train"]))
    x_train = transform_features(pre, make_feature_frame(splits["train"]))
    x_validation = transform_features(pre, make_feature_frame(splits["validation"]))
    y_train = splits["train"][config.TARGET].to_numpy(dtype=float)
    y_validation = splits["validation"][config.TARGET].to_numpy(dtype=float)

    scores: dict[str, tuple[float, float]] = {}
    for params in config.MODEL_GRIDS["random_forest"]:
        estimator = build_model("random_forest", params, 11)
        estimator.fit(x_train, y_train)
        scores[json.dumps(params, sort_keys=True)] = (
            float(estimator.score(x_train, y_train)),
            float(estimator.score(x_validation, y_validation)),
        )

    best_by_train = max(scores, key=lambda key: scores[key][0])
    best_by_validation = max(scores, key=lambda key: scores[key][1])
    assert best_by_train != best_by_validation, (
        "this fixture cannot distinguish training-based from validation-based selection"
    )

    chosen = fit_model("random_forest", splits, seed=11).params
    assert json.dumps(chosen, sort_keys=True) == best_by_validation
