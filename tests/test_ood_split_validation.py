"""Held-out family, split integrity and validation-report branches (D-OOD, D-SPL, D-VAL)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import config


# --------------------------------------------------------------------------- held-out family
def test_ood_row_count_and_labelling() -> None:
    from src.simulate_data import simulate_ood

    frame = simulate_ood(seed=11, n_scenarios=20)
    assert len(frame) == 20 * config.N_REPLICATES
    assert frame["scenario_id"].nunique() == 20
    assert (frame["split"] == "ood").all()
    assert (frame["data_provenance"] == "synthetic").all()


def test_ood_is_deterministic() -> None:
    from src.simulate_data import simulate_ood

    pd.testing.assert_frame_equal(simulate_ood(seed=11, n_scenarios=15), simulate_ood(seed=11, n_scenarios=15))
    assert not simulate_ood(seed=11, n_scenarios=15)[config.TARGET].equals(
        simulate_ood(seed=12, n_scenarios=15)[config.TARGET]
    )


def test_ood_lies_outside_the_training_support_on_two_axes() -> None:
    from src.simulate_data import simulate_ood

    frame = simulate_ood(seed=11, n_scenarios=60)
    per = frame.groupby("scenario_id", as_index=False).first()
    assert per["total_solids_pct"].min() > config.INPUT_RANGES["total_solids_pct"][1] - 1e-9
    assert per["lipid_fraction"].min() >= 0.30 - 1e-9
    # the other axes stay inside their training ranges: the held-out set is not a different world
    assert per["temperature_c"].between(*config.INPUT_RANGES["temperature_c"]).all()
    assert per["olr_kg_vs_m3_d"].between(*config.INPUT_RANGES["olr_kg_vs_m3_d"]).all()


def test_ood_outputs_are_low_but_not_degenerate() -> None:
    """SPEC_V1 4.1 (iii): the held-out family is low but contains no exact zeros."""
    from src.simulate_data import simulate_ood

    per = simulate_ood(seed=11, n_scenarios=60).groupby("scenario_id", as_index=False).first()
    values = per[config.TARGET]
    assert 20.0 < values.mean() < 400.0, values.mean()
    assert values.min() > 0.0
    assert int((values <= 0.0).sum()) == 0
    assert values.max() / values.min() > 5.0, "family collapsed to a single value"


def test_ood_composition_sums_to_one() -> None:
    from src.simulate_data import simulate_ood

    frame = simulate_ood(seed=11, n_scenarios=25)
    total = frame["carb_fraction"] + frame["protein_fraction"] + frame["lipid_fraction"]
    assert np.allclose(total.to_numpy(), 1.0, atol=1e-9)


def test_ood_frames_validate_against_the_ood_envelope() -> None:
    from src.simulate_data import simulate_ood, validate_frame

    frame = simulate_ood(seed=23, n_scenarios=30)
    report = validate_frame(frame, ranges=config.OOD_RANGES)
    assert report["ok"] is True, report["checks_failed"]
    assert report["envelope"] == "ood"
    # the training envelope must reject it - that is what makes it held out
    training = validate_frame(frame)
    assert training["ok"] is False
    assert training["envelope"] == "training"


def test_ood_non_extended_axes_stay_inside_the_central_bands() -> None:
    from src.simulate_data import simulate_ood

    per = simulate_ood(seed=11, n_scenarios=60).groupby("scenario_id", as_index=False).first()
    for column, (low, high) in config.OOD_CENTRAL_BANDS.items():
        assert per[column].min() >= low - 1e-9, column
        assert per[column].max() <= high + 1e-9, column


def test_ood_guard_raises_when_the_pool_is_too_small() -> None:
    from src.simulate_data import simulate_ood

    with pytest.raises(RuntimeError):
        simulate_ood(seed=11, n_scenarios=500, _pool_factor=1.0)


# --------------------------------------------------------------------------- split integrity
def test_split_is_scenario_grouped() -> None:
    from src.simulate_data import simulate

    frame, _ = simulate(seed=11, n_scenarios=120)
    labels_per_scenario = frame.groupby("scenario_id")["split"].nunique()
    assert (labels_per_scenario == 1).all()


def test_split_fractions_and_disjointness() -> None:
    from src.simulate_data import simulate

    frame, _ = simulate(seed=11, n_scenarios=200)
    per = frame.groupby("scenario_id", as_index=False).first()
    counts = per["split"].value_counts(normalize=True)
    assert counts["train"] == pytest.approx(0.70, abs=0.03)
    assert counts["validation"] == pytest.approx(0.15, abs=0.03)
    assert counts["test"] == pytest.approx(0.15, abs=0.03)
    assert set(per["split"]) == {"train", "validation", "test"}


def test_split_is_deterministic_and_seed_dependent() -> None:
    from src.simulate_data import assign_split

    ids = np.array([f"S{i:05d}" for i in range(50)])
    assert list(assign_split(ids, 11)) == list(assign_split(ids, 11))
    assert list(assign_split(ids, 11)) != list(assign_split(ids, 23))


def test_no_scenario_appears_in_two_splits_across_seeds_is_not_required() -> None:
    """Documented non-requirement: seeds are separate experiments, not pooled."""
    from src.simulate_data import simulate

    a, _ = simulate(seed=11, n_scenarios=40)
    b, _ = simulate(seed=23, n_scenarios=40)
    assert set(a["scenario_id"]) == set(b["scenario_id"])


# --------------------------------------------------------------------------- validation branches
def test_validate_reports_missing_input_column(small_frame: pd.DataFrame) -> None:
    from src.simulate_data import validate_frame

    report = validate_frame(small_frame.drop(columns=["temperature_c"]))
    assert report["ok"] is False
    assert any("temperature_c" in c for c in report["checks_failed"])


def test_validate_skips_composition_check_when_a_fraction_is_absent(small_frame: pd.DataFrame) -> None:
    from src.simulate_data import validate_frame

    report = validate_frame(small_frame.drop(columns=["lipid_fraction"]))
    assert report["ok"] is False
    assert not any("sum to one" in c for c in report["checks_failed"])


def test_validate_reports_target_outside_bounds(small_frame: pd.DataFrame) -> None:
    from src.simulate_data import validate_frame

    broken = small_frame.copy()
    broken.loc[broken.index[0], config.TARGET] = config.YIELD_MAX + 50.0
    report = validate_frame(broken)
    assert any("physical bounds" in c for c in report["checks_failed"])


def test_validate_reports_missing_target_values(small_frame: pd.DataFrame) -> None:
    from src.simulate_data import validate_frame

    broken = small_frame.copy()
    broken.loc[broken.index[0], config.TARGET] = np.nan
    report = validate_frame(broken)
    assert any("missing values" in c for c in report["checks_failed"])


def test_validate_handles_frames_without_the_target(small_frame: pd.DataFrame) -> None:
    from src.simulate_data import validate_frame

    report = validate_frame(small_frame.drop(columns=[config.TARGET]))
    assert report["ok"] is False
    assert any("missing column" in c for c in report["checks_failed"])
    assert not any("missing values" in c for c in report["checks_failed"])


def test_validate_reports_stability_outside_unit_interval(small_frame: pd.DataFrame) -> None:
    from src.simulate_data import validate_frame

    broken = small_frame.copy()
    broken.loc[broken.index[0], "simulated_stability_indicator"] = 1.5
    report = validate_frame(broken)
    assert any("stability" in c for c in report["checks_failed"])


def test_validate_handles_frames_without_stability(small_frame: pd.DataFrame) -> None:
    from src.simulate_data import validate_frame

    report = validate_frame(small_frame.drop(columns=["simulated_stability_indicator"]))
    assert not any("stability" in c for c in report["checks_failed"])


def test_validate_reports_composition_breach(small_frame: pd.DataFrame) -> None:
    from src.simulate_data import validate_frame

    broken = small_frame.copy()
    broken.loc[broken.index[0], "carb_fraction"] = 0.10
    report = validate_frame(broken)
    assert any("sum to one" in c for c in report["checks_failed"])


def test_validate_reports_biogas_column_absence_without_mass_balance_claim(
    small_frame: pd.DataFrame,
) -> None:
    from src.simulate_data import validate_frame

    report = validate_frame(small_frame.drop(columns=["simulated_methane_fraction"]))
    assert not any("mass balance" in c for c in report["checks_failed"])


def test_validate_reports_row_and_scenario_counts(small_frame: pd.DataFrame) -> None:
    from src.simulate_data import validate_frame

    report = validate_frame(small_frame)
    assert report["n_rows"] == len(small_frame)
    assert report["n_scenarios"] == small_frame["scenario_id"].nunique()
