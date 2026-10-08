"""Splitting, leakage guards, preprocessing, the five models and the pipeline controls.

Implements the frozen protocol of `docs/model_specification.md` §9 (splitting, train-only
preprocessing, tuning inside train/validation, the five models) and the pipeline controls of §12
(permuted-target control, duplicate-row guard).

Everything trained here learns a **simulator**, not a digester. Artifact metadata says so.

CLI
---
    python -m src.train_models --seed 11 --outdir results/models
"""

from __future__ import annotations

import argparse
import json
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

from src import config
from src.simulate_data import simulate

SPLIT_NAMES: tuple[str, ...] = ("train", "validation", "test", "ood")

#: Columns that must never reach a model. Three separate reasons, kept separate on purpose.
LEAKY_COLUMNS: frozenset[str] = frozenset(
    (*config.LATENT_COLUMNS, *config.META_COLUMNS)  # leak: they encode the answer or the provenance
)
DERIVED_COLUMNS: frozenset[str] = frozenset(config.DIAGNOSTIC_COLUMNS)
OUTPUT_COLUMNS: frozenset[str] = frozenset((*config.OUTPUT_COLUMNS, config.TARGET))


# ============================================================================ splitting


def split_frame(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Split by the declared `split` labels; a scenario's replicates stay together."""
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("frame must be a pandas DataFrame")
    if "split" not in frame.columns:
        raise ValueError("frame has no `split` column; generate it with src.simulate_data")
    unknown = sorted(set(frame["split"]) - set(SPLIT_NAMES))
    if unknown:
        raise ValueError(f"unknown split label(s): {unknown}")
    parts = {name: frame[frame["split"] == name].reset_index(drop=True) for name in SPLIT_NAMES}
    parts = {name: part for name, part in parts.items() if len(part) > 0}
    if not {"train", "validation", "test"} <= set(parts):
        raise ValueError("frame is missing one of train/validation/test")
    assert_no_group_overlap(parts)
    return parts


def assert_no_group_overlap(parts: dict[str, pd.DataFrame]) -> None:
    """Raise if a scenario appears in more than one split (SPEC_V1 §9 step 1)."""
    seen: dict[str, list[str]] = {}
    for name, part in parts.items():
        for scenario_id in set(part["scenario_id"]):
            seen.setdefault(str(scenario_id), []).append(name)
    offenders = {sid: names for sid, names in seen.items() if len(names) > 1}
    if offenders:
        example = next(iter(offenders.items()))
        raise ValueError(
            f"scenario overlap between splits ({len(offenders)} scenarios, e.g. {example[0]} in "
            f"{example[1]}); the split must be grouped by scenario"
        )


def _scaled_feature_matrix(frame: pd.DataFrame) -> np.ndarray:
    """Features scaled by their declared range widths, so a distance is comparable across units."""
    features = make_feature_frame(frame).to_numpy(dtype=float)
    # missing measurements get one shared sentinel so that two rows missing the same field are
    # not treated as distinct, and so the distance computation stays finite
    features = np.nan_to_num(features, nan=-999.0)
    widths = np.array(
        [
            max(config.INPUT_RANGES[c][1] - config.INPUT_RANGES[c][0], 1e-12)
            for c in config.FEATURES
        ]
    )
    return features / widths


def cross_split_duplicate_report(
    parts: dict[str, pd.DataFrame], tolerance: float = 0.0
) -> dict[str, Any]:
    """SPEC_V1 §12 control 2: near-duplicate rows must not straddle two splits.

    Returns the number of feature-vector groups that appear in more than one split, and the
    smallest cross-split distance (range-normalised Euclidean). Exact duplicates are found by
    hashing the recorded feature vectors; the minimum distance uses a KD-tree over the training
    split, so it is exact rather than sampled.
    """
    names = [name for name in ("train", "validation", "test") if name in parts]
    matrices = {name: _scaled_feature_matrix(parts[name]) for name in names}

    groups: dict[bytes, set[str]] = {}
    for name, matrix in matrices.items():
        for row in matrix:
            groups.setdefault(np.round(row, 9).tobytes(), set()).add(name)
    n_exact_cross_split = sum(1 for splits_seen in groups.values() if len(splits_seen) > 1)

    min_distance = float("inf")
    for i, reference in enumerate(names):
        tree = cKDTree(matrices[reference])
        for other in names[i + 1 :]:
            distances, _ = tree.query(matrices[other], k=1)
            min_distance = min(min_distance, float(np.min(distances)))

    return {
        "n_exact_cross_split": n_exact_cross_split,
        "min_cross_split_distance": min_distance,
        "tolerance": tolerance,
        "n_rows": {name: len(part) for name, part in parts.items()},
    }


# ============================================================================ leakage guard


def check_feature_columns(columns: list[str] | tuple[str, ...]) -> None:
    """Reject anything that is not a declared model input, with the reason named."""
    for column in columns:
        if column in LEAKY_COLUMNS:
            raise ValueError(
                f"{column!r} leaks information (latent factor or provenance column) and is not "
                "permitted as a model input"
            )
        if column in DERIVED_COLUMNS:
            raise ValueError(
                f"{column!r} is a derived diagnostic computed from the inputs, not a declared "
                "model input"
            )
        if column in OUTPUT_COLUMNS:
            raise ValueError(f"{column!r} is an output or the target, not a model input")
        if column not in config.FEATURES:
            raise ValueError(f"{column!r} is an unknown column; only config.FEATURES may be used")


def make_feature_frame(
    frame: pd.DataFrame, columns: list[str] | tuple[str, ...] | None = None
) -> pd.DataFrame:
    """Return the model-facing feature matrix, with the leakage guard applied."""
    chosen = list(config.FEATURES if columns is None else columns)
    check_feature_columns(chosen)
    missing = [column for column in chosen if column not in frame.columns]
    if missing:
        raise KeyError(f"frame is missing feature column(s): {missing}")
    return frame.loc[:, chosen].astype(float)


# ============================================================================ preprocessing


@dataclass
class FeaturePreprocessor:
    """Median imputation followed by standardisation, both fit on the training split only.

    The two steps are kept as separate, inspectable objects (`imputer`, `scaler`) so that the
    train-only rule can be *asserted* rather than assumed - the tests read their fitted
    statistics and compare them with the full-data statistics they must not equal.
    """

    imputer: SimpleImputer = field(default_factory=lambda: SimpleImputer(strategy="median"))
    scaler: StandardScaler = field(default_factory=StandardScaler)

    def fit(self, train_features: pd.DataFrame) -> FeaturePreprocessor:
        if not isinstance(train_features, pd.DataFrame):
            raise TypeError("train_features must be a pandas DataFrame")
        if train_features.empty:
            raise ValueError("cannot fit preprocessing on an empty training frame")
        check_feature_columns(list(train_features.columns))
        self.imputer.fit(train_features)
        self.scaler.fit(self.imputer.transform(train_features))
        return self

    def transform(self, features: pd.DataFrame) -> np.ndarray:
        return np.asarray(self.scaler.transform(self.imputer.transform(features)), dtype=float)


def fit_preprocessor(train_features: pd.DataFrame) -> FeaturePreprocessor:
    """Fit imputation and scaling **on the training split only** (SPEC_V1 §9 step 2)."""
    return FeaturePreprocessor().fit(train_features)


def transform_features(preprocessor: FeaturePreprocessor, features: pd.DataFrame) -> np.ndarray:
    """Apply a fitted preprocessor; returns a dense array of shape (n_rows, n_features)."""
    return preprocessor.transform(features)


# ============================================================================ models


@dataclass
class FittedModel:
    """A tuned estimator plus the preprocessing it was trained behind.

    `preprocessor` is fit **on the training split only** (SPEC_V1 §9 step 2) and is frozen before
    the estimator is fit; the estimator itself is fit on the transformed rows of train +
    validation. Keeping the two objects separate makes that rule auditable rather than implied.
    """

    name: str
    estimator: Any
    params: dict[str, Any]
    preprocessor: FeaturePreprocessor
    fit_rows: int
    seed: int
    tuning_log: list[dict[str, Any]] = field(default_factory=list)
    convergence_warnings: int = 0

    @property
    def features(self) -> list[str]:
        return list(config.FEATURES)


def build_model(name: str, params: dict[str, Any], seed: int) -> Any:
    """Construct one of the five declared estimators. Anything else is rejected by name."""
    if name not in config.MODEL_NAMES:
        raise ValueError(
            f"unknown model {name!r}; the five declared models are {config.MODEL_NAMES}"
        )
    if name == "dummy":
        return DummyRegressor(strategy="mean")
    if name == "ridge":
        return Ridge(**params)
    if name == "random_forest":
        return RandomForestRegressor(random_state=seed, n_jobs=1, **params)
    if name == "hist_gradient_boosting":
        return HistGradientBoostingRegressor(random_state=seed, **params)
    # max_iter stays at 2000: measured on this simulator, raising the cap to 5000 still did not
    # satisfy sklearn's tolerance criterion and made validation R2 worse (0.56 vs 0.63 on a
    # 250-scenario split), so the non-convergence is recorded rather than tuned away.
    return MLPRegressor(random_state=seed, max_iter=2000, early_stopping=False, **params)


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    """R², MAE, RMSE and n. R² is `None` when it is undefined (constant target), never 0."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    if y_true.shape != y_pred.shape:
        raise ValueError(f"shape mismatch: y_true {y_true.shape} vs y_pred {y_pred.shape}")
    residual = y_true - y_pred
    ss_res = float(np.sum(residual**2))
    ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
    r2: float | None = None if ss_tot == 0.0 else 1.0 - ss_res / ss_tot
    return {
        "r2": r2,
        "mae": float(np.mean(np.abs(residual))),
        "rmse": float(np.sqrt(np.mean(residual**2))),
        "n": int(y_true.size),
        "target_std": float(y_true.std()),
    }


def _design(
    split: pd.DataFrame, preprocessor: FeaturePreprocessor
) -> tuple[np.ndarray, np.ndarray]:
    features = transform_features(preprocessor, make_feature_frame(split))
    return features, split[config.TARGET].to_numpy(dtype=float)


def tune_model(
    name: str,
    splits: dict[str, pd.DataFrame],
    seed: int,
    preprocessor: FeaturePreprocessor | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], FeaturePreprocessor]:
    """Select hyper-parameters on train/validation only. The test split is never read."""
    if name not in config.MODEL_NAMES:
        raise ValueError(
            f"unknown model {name!r}; the five declared models are {config.MODEL_NAMES}"
        )
    pre = (
        fit_preprocessor(make_feature_frame(splits["train"]))
        if preprocessor is None
        else preprocessor
    )
    x_train, y_train = _design(splits["train"], pre)
    x_validation, y_validation = _design(splits["validation"], pre)

    log: list[dict[str, Any]] = []
    best_params = config.MODEL_GRIDS[name][0]
    best_score = -np.inf
    for params in config.MODEL_GRIDS[name]:
        estimator = build_model(name, params, seed)
        estimator.fit(x_train, y_train)
        train_r2 = float(estimator.score(x_train, y_train))
        validation_r2 = float(estimator.score(x_validation, y_validation))
        log.append({"params": dict(params), "train_r2": train_r2, "validation_r2": validation_r2})
        if validation_r2 > best_score:
            best_score, best_params = validation_r2, params
    return dict(best_params), log, pre


def fit_model(name: str, splits: dict[str, pd.DataFrame], seed: int) -> FittedModel:
    """Tune on train/validation, then refit the chosen configuration on train + validation."""
    preprocessor = fit_preprocessor(make_feature_frame(splits["train"]))
    params, log, _ = tune_model(name, splits, seed, preprocessor=preprocessor)
    combined = pd.concat([splits["train"], splits["validation"]], ignore_index=True)
    x_combined, y_combined = _design(combined, preprocessor)
    estimator = build_model(name, params, seed)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        estimator.fit(x_combined, y_combined)
    convergence_warnings = sum(
        1 for warning in caught if issubclass(warning.category, ConvergenceWarning)
    )

    return FittedModel(
        name=name,
        estimator=estimator,
        params=params,
        preprocessor=preprocessor,
        fit_rows=len(combined),
        seed=seed,
        tuning_log=log,
        convergence_warnings=convergence_warnings,
    )


def fit_all_models(
    splits: dict[str, pd.DataFrame],
    seed: int,
    names: tuple[str, ...] | None = None,
) -> dict[str, FittedModel]:
    """Fit the five declared models. `names` exists for tests; it cannot add a sixth model."""
    chosen = config.MODEL_NAMES if names is None else names
    for name in chosen:
        if name not in config.MODEL_NAMES:
            raise ValueError(
                f"unknown model {name!r}; the five declared models are {config.MODEL_NAMES}"
            )
    return {name: fit_model(name, splits, seed) for name in chosen}


def predict_model(model: FittedModel, features: pd.DataFrame) -> np.ndarray:
    """Predict with a fitted model, applying the frozen training-time preprocessing."""
    design = transform_features(model.preprocessor, make_feature_frame(features))
    return np.asarray(model.estimator.predict(design), dtype=float)


# ============================================================================ persistence


def _artifact_metadata(model: FittedModel) -> dict[str, Any]:
    return {
        "marker": config.SIMULATED_MARKER,
        "data_provenance": config.DATA_PROVENANCE,
        "simulator_version": config.SIMULATOR_VERSION,
        "as_of": config.AS_OF,
        "model": model.name,
        "params": {k: (list(v) if isinstance(v, tuple) else v) for k, v in model.params.items()},
        "seed": model.seed,
        "fit_rows": model.fit_rows,
        "features": model.features,
        "target": config.TARGET,
        "scale_adoption_note": config.SCALE_ADOPTION_NOTE,
        "limitation": (
            "Trained on SIMULATED data. This artifact learns the assumptions of the simulator, "
            "not the behaviour of a real digester; its scores are not evidence about real food "
            "waste or real biogas yields."
        ),
        "tuning_log": model.tuning_log,
        "convergence_warnings": model.convergence_warnings,
        "training_notes": (
            "The estimator reported ConvergenceWarning(s) while fitting (sklearn's tolerance "
            "criterion was not met). The scores are reported with that caveat; raising the "
            "iteration cap did not improve validation performance in the measured case."
            if model.convergence_warnings
            else "No convergence warnings were raised while fitting."
        ),
        "simulated": True,
    }


def save_model(model: FittedModel, directory: Path | str) -> Path:
    """Write `<model>.joblib` plus its metadata sidecar; returns the artifact path."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{model.name}.joblib"
    joblib.dump(model, path)
    (directory / f"{model.name}.json").write_text(
        json.dumps(_artifact_metadata(model), indent=2, default=str), encoding="utf-8"
    )
    return path


def load_model(path: Path | str) -> FittedModel:
    """Load a fitted model artifact written by `save_model`."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"no model artifact at {path}")
    return joblib.load(path)


# ============================================================================ controls


def run_permuted_target_control(
    splits: dict[str, pd.DataFrame],
    seed: int,
    names: tuple[str, ...] = ("ridge", "random_forest"),
    n_permutations: int = 5,
) -> dict[str, dict[str, Any]]:
    """SPEC_V1 §12 control 1: with the training target shuffled, skill must vanish.

    A single permutation can score slightly positive by chance on a small test split (observed:
    Ridge +0.066 on one draw), so the control is run `n_permutations` times and the reported
    statistic is the mean, with the min and max kept visible. Skill that survives permuting the
    target would indicate leakage, not signal.
    """
    rng = np.random.default_rng(seed + 7777)
    pre = fit_preprocessor(make_feature_frame(splits["train"]))
    x_test, y_test = _design(splits["test"], pre)

    per_model: dict[str, list[float]] = {name: [] for name in names}
    for _ in range(n_permutations):
        permuted = {name: part.copy() for name, part in splits.items()}
        for part_name in ("train", "validation"):
            values = permuted[part_name][config.TARGET].to_numpy(dtype=float)
            permuted[part_name][config.TARGET] = rng.permutation(values)
        for name in names:
            params, _, _ = tune_model(name, permuted, seed, preprocessor=pre)
            combined = pd.concat([permuted["train"], permuted["validation"]], ignore_index=True)
            x_combined, y_combined = _design(combined, pre)
            estimator = build_model(name, params, seed)
            estimator.fit(x_combined, y_combined)
            per_model[name].append(float(r2_score(y_test, estimator.predict(x_test))))

    return {
        name: {
            "mean_r2": float(np.mean(values)),
            "min_r2": float(np.min(values)),
            "max_r2": float(np.max(values)),
            "n_permutations": n_permutations,
        }
        for name, values in per_model.items()
    }


# ============================================================================ CLI


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.train_models",
        description="Fit the five declared models to SIMULATED data (SPEC_V1 §9).",
    )
    parser.add_argument("--seed", type=int, default=config.SEEDS[0])
    parser.add_argument("--n-scenarios", type=int, default=config.N_SCENARIOS)
    parser.add_argument("--outdir", type=Path, default=config.MODELS_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    frame, _ = simulate(seed=args.seed, n_scenarios=args.n_scenarios)
    splits = split_frame(frame)
    report = cross_split_duplicate_report(splits)
    if report["n_exact_cross_split"]:
        print(
            f"warning: {report['n_exact_cross_split']} feature-vector group(s) appear "
            "in two splits [SIMULATED data]"
        )
    fitted = fit_all_models(splits, seed=args.seed)
    for name, model in fitted.items():
        path = save_model(model, args.outdir)
        metrics = regression_metrics(
            splits["test"][config.TARGET].to_numpy(dtype=float),
            predict_model(model, splits["test"]),
        )
        r2 = "undefined" if metrics["r2"] is None else f"{metrics['r2']:.4f}"
        print(
            f"{name}: wrote {path} | test R2={r2} "
            f"MAE={metrics['mae']:.2f} RMSE={metrics['rmse']:.2f} [SIMULATED]"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
