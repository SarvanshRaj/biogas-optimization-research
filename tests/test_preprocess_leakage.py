"""Splitting, leakage guard, preprocessing and pipeline controls (matrix groups D-SPL, D-PRE, D-CTL).

These tests are written against the frozen protocol in `docs/model_specification.md` §9 and the
control list in §12. They exercise the *checks*, including a mutation test that proves the
"fit on training data only" rule is actually detectable rather than merely asserted.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import config
from src.simulate_data import simulate


@pytest.fixture(scope="module")
def frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    return simulate(seed=11, n_scenarios=60)


@pytest.fixture(scope="module")
def splits(frames: tuple[pd.DataFrame, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    from src.train_models import split_frame

    return split_frame(frames[0])


@pytest.fixture(scope="module")
def splits_large() -> dict[str, pd.DataFrame]:
    """A larger split, needed where the train-vs-full statistics must differ measurably."""
    from src.train_models import split_frame

    return split_frame(simulate(seed=11, n_scenarios=250)[0])


# --------------------------------------------------------------------------- splitting
def test_split_returns_the_three_declared_parts(splits: dict[str, pd.DataFrame]) -> None:
    assert set(splits) >= {"train", "validation", "test"}
    for name, part in splits.items():
        assert len(part) > 0, name


def test_split_is_a_tri_partition_of_scenarios(splits: dict[str, pd.DataFrame]) -> None:
    ids = [set(part["scenario_id"]) for part in splits.values()]
    union: set[str] = set()
    for part in ids:
        union |= part
    assert sum(len(p) for p in ids) == len(union), "a scenario appears in two splits"
    assert len(union) == 60


def test_split_keeps_replicates_together(splits: dict[str, pd.DataFrame]) -> None:
    for part in splits.values():
        counts = part.groupby("scenario_id").size().unique()
        assert list(counts) == [config.N_REPLICATES]


def test_split_proportions_match_the_frozen_rule(splits: dict[str, pd.DataFrame]) -> None:
    total = sum(len(p["scenario_id"].unique()) for p in splits.values())
    train_share = splits["train"]["scenario_id"].nunique() / total
    assert train_share == pytest.approx(0.70, abs=0.05)


def test_group_overlap_check_passes_on_a_real_split(splits: dict[str, pd.DataFrame]) -> None:
    from src.train_models import assert_no_group_overlap

    assert_no_group_overlap(splits)  # must not raise


def test_group_overlap_check_is_not_a_no_op(splits: dict[str, pd.DataFrame]) -> None:
    """Negative control: the check must reject a split with a shared scenario."""
    from src.train_models import assert_no_group_overlap

    poisoned = {k: v.copy() for k, v in splits.items()}
    poisoned["test"] = pd.concat([poisoned["test"], poisoned["train"].head(3)], ignore_index=True)
    with pytest.raises(ValueError, match="scenario"):
        assert_no_group_overlap(poisoned)


def test_split_labels_must_be_known(splits: dict[str, pd.DataFrame]) -> None:
    from src.train_models import split_frame

    broken = pd.concat([splits["train"], splits["validation"]], ignore_index=True)
    broken.loc[broken.index[0], "split"] = "holdout"
    with pytest.raises(ValueError, match="unknown split label"):
        split_frame(broken)


def test_split_frame_rejects_non_dataframe() -> None:
    from src.train_models import split_frame

    with pytest.raises(TypeError):
        split_frame([1, 2, 3])  # type: ignore[arg-type]


def test_ood_is_kept_in_its_own_part() -> None:
    from src.simulate_data import simulate_ood
    from src.train_models import split_frame

    combined = pd.concat([simulate(seed=11, n_scenarios=20)[0], simulate_ood(seed=11, n_scenarios=5)])
    parts = split_frame(combined)
    assert "ood" in parts
    assert set(parts["ood"]["split"]) == {"ood"}
    assert not set(parts["ood"]["scenario_id"]) & set(parts["train"]["scenario_id"])


# --------------------------------------------------------------------------- duplicate guard
def test_cross_split_duplicate_guard_runs_on_real_data(splits: dict[str, pd.DataFrame]) -> None:
    """SPEC_V1 §12 control 2: near-duplicate rows must not straddle splits."""
    from src.train_models import cross_split_duplicate_report

    report = cross_split_duplicate_report(splits, tolerance=0.0)
    assert report["n_exact_cross_split"] == 0
    assert report["min_cross_split_distance"] > 0.0


def test_cross_split_duplicate_guard_detects_an_injected_duplicate(splits: dict[str, pd.DataFrame]) -> None:
    from src.train_models import cross_split_duplicate_report

    poisoned = {k: v.copy() for k, v in splits.items()}
    twin = poisoned["test"].head(1).copy()
    twin["scenario_id"] = "S99999"
    poisoned["train"] = pd.concat([poisoned["train"], twin], ignore_index=True)
    report = cross_split_duplicate_report(poisoned, tolerance=0.0)
    assert report["n_exact_cross_split"] >= 1


# --------------------------------------------------------------------------- leakage guard
def test_feature_columns_are_exactly_the_declared_features(splits: dict[str, pd.DataFrame]) -> None:
    from src.train_models import make_feature_frame

    features = make_feature_frame(splits["train"])
    assert list(features.columns) == list(config.FEATURES)


def test_latent_and_diagnostic_columns_are_rejected(splits: dict[str, pd.DataFrame]) -> None:
    from src.train_models import LEAKY_COLUMNS, make_feature_frame

    frame = splits["train"].copy()
    for column in config.LATENT_COLUMNS:
        assert column in LEAKY_COLUMNS
    # simulate the mistake: a frame that still carries the latent factors
    for column in config.LATENT_COLUMNS:
        frame[column] = 1.0
    with pytest.raises(ValueError, match="leak"):
        make_feature_frame(frame, columns=list(config.FEATURES) + list(config.LATENT_COLUMNS))


def test_output_and_target_columns_are_rejected_as_features() -> None:
    from src.train_models import check_feature_columns

    for column in (config.TARGET, "simulated_methane_fraction", "simulated_stability_indicator"):
        with pytest.raises(ValueError):
            check_feature_columns([*config.FEATURES, column])


def test_unknown_column_is_rejected() -> None:
    from src.train_models import check_feature_columns

    with pytest.raises(ValueError, match="unknown"):
        check_feature_columns([*config.FEATURES, "not_a_column"])


def test_diagnostic_columns_are_rejected() -> None:
    from src.train_models import check_feature_columns

    for column in config.DIAGNOSTIC_COLUMNS:
        with pytest.raises(ValueError):
            check_feature_columns([*config.FEATURES, column])


def test_feature_frame_has_no_missing_after_imputation(splits: dict[str, pd.DataFrame]) -> None:
    from src.train_models import fit_preprocessor, make_feature_frame, transform_features

    train = make_feature_frame(splits["train"])
    pre = fit_preprocessor(train)
    transformed = transform_features(pre, make_feature_frame(splits["test"]))
    assert np.isfinite(transformed).all()


def test_feature_frame_raises_when_a_feature_is_absent(splits: dict[str, pd.DataFrame]) -> None:
    from src.train_models import make_feature_frame

    with pytest.raises(KeyError):
        make_feature_frame(splits["train"].drop(columns=["temperature_c"]))


# --------------------------------------------------------------------------- train-only fitting
def test_imputer_statistics_come_from_train_only(splits_large: dict[str, pd.DataFrame]) -> None:
    from src.train_models import fit_preprocessor, make_feature_frame

    train = make_feature_frame(splits_large["train"])
    pre = fit_preprocessor(train)
    imputer = pre.imputer
    assert imputer.statistics_ is not None
    idx = list(config.FEATURES).index("ph_measured")
    assert imputer.statistics_[idx] == pytest.approx(train["ph_measured"].median())

    full = pd.concat([make_feature_frame(p) for p in splits_large.values()])
    assert imputer.statistics_[idx] != pytest.approx(full["ph_measured"].median()), (
        "train median and full-data median are indistinguishable in this fixture; "
        "pick a fixture where the mutation test has power"
    )


def test_scaler_statistics_come_from_train_only(splits: dict[str, pd.DataFrame]) -> None:
    from src.train_models import fit_preprocessor, make_feature_frame

    train = make_feature_frame(splits["train"])
    pre = fit_preprocessor(train)
    scaler = pre.scaler
    assert scaler.mean_ is not None
    idx = list(config.FEATURES).index("total_solids_pct")
    assert scaler.mean_[idx] == pytest.approx(train["total_solids_pct"].mean())
    full = pd.concat([make_feature_frame(p) for p in splits.values()])
    assert scaler.mean_[idx] != pytest.approx(full["total_solids_pct"].mean())


def test_imputation_uses_the_training_median_exactly(splits: dict[str, pd.DataFrame]) -> None:
    from src.train_models import fit_preprocessor, make_feature_frame, transform_features

    train = make_feature_frame(splits["train"])
    pre = fit_preprocessor(train)
    scaler = pre.scaler
    imputer = pre.imputer
    assert scaler.mean_ is not None and scaler.scale_ is not None
    assert imputer.statistics_ is not None

    probe = make_feature_frame(splits["test"]).head(1).copy()
    probe.loc[probe.index[0], "ph_measured"] = np.nan
    row = transform_features(pre, probe)[0]
    idx = list(config.FEATURES).index("ph_measured")
    expected = (imputer.statistics_[idx] - scaler.mean_[idx]) / scaler.scale_[idx]
    assert row[idx] == pytest.approx(expected)


def test_preprocessor_mutation_is_detectable(splits: dict[str, pd.DataFrame]) -> None:
    """Mutation test: a *full-data* fit must be distinguishable from the train-only fit.

    If this ever passes silently (i.e. the two fits coincide) the leakage assertion above would
    be vacuous, so the power of the check is itself asserted here.
    """
    from sklearn.preprocessing import StandardScaler

    from src.train_models import fit_preprocessor, make_feature_frame

    train = make_feature_frame(splits["train"])
    test = make_feature_frame(splits["test"])
    honest = fit_preprocessor(train).scaler
    assert honest.mean_ is not None
    mutated = StandardScaler().fit(pd.concat([train, test]).to_numpy())
    assert mutated.mean_ is not None
    assert np.abs(honest.mean_ - mutated.mean_).max() > 1e-6
    with pytest.raises(AssertionError):
        np.testing.assert_allclose(honest.mean_, mutated.mean_, atol=1e-6)


def test_preprocessor_rejects_an_empty_training_frame() -> None:
    from src.train_models import fit_preprocessor

    with pytest.raises(ValueError):
        fit_preprocessor(pd.DataFrame(columns=list(config.FEATURES)))


def test_constant_column_survives_scaling() -> None:
    from src.train_models import fit_preprocessor, transform_features

    frame = pd.DataFrame({column: np.arange(10.0) for column in config.FEATURES})
    frame["inoculum_ratio"] = 2.0  # constant: zero variance
    transformed = transform_features(fit_preprocessor(frame), frame)
    assert np.isfinite(transformed).all()
    idx = list(config.FEATURES).index("inoculum_ratio")
    assert np.allclose(transformed[:, idx], 0.0)


# --------------------------------------------------------------------------- permuted control
def test_permuted_target_control_removes_skill(splits_large: dict[str, pd.DataFrame]) -> None:
    """SPEC_V1 §12 control 1: with shuffled training targets the pipeline must not find signal.

    The tolerance is deliberately not zero: a single chance permutation can score slightly
    positive on a small test split (observed +0.066 for Ridge), which is why the statistic is
    the mean over five permutations and the worst draw is kept visible.
    """
    from src.train_models import run_permuted_target_control

    result = run_permuted_target_control(
        splits_large, seed=11, names=("ridge", "random_forest"), n_permutations=5
    )
    assert set(result) == {"ridge", "random_forest"}
    for name, stats in result.items():
        assert stats["n_permutations"] == 5
        assert stats["mean_r2"] <= 0.05, f"{name} averaged skill from a permuted target: {stats}"
        assert stats["max_r2"] <= 0.15, f"{name} found skill in a permuted target: {stats}"


def test_permuted_control_separates_cleanly_from_the_real_target(
    splits_large: dict[str, pd.DataFrame],
) -> None:
    """The gap between permuted and real skill is the evidence that the control has power."""
    from sklearn.metrics import r2_score

    from src.train_models import (
        fit_model,
        make_feature_frame,
        predict_model,
        run_permuted_target_control,
    )

    permuted = run_permuted_target_control(splits_large, seed=11, names=("ridge",))
    model = fit_model("ridge", splits_large, seed=11)
    real = float(
        r2_score(
            splits_large["test"][config.TARGET],
            predict_model(model, make_feature_frame(splits_large["test"])),
        )
    )
    assert real > permuted["ridge"]["mean_r2"] + 0.15, (real, permuted)
