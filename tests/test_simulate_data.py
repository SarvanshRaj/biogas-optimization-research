"""Simulator contract tests.

Covers test-matrix groups: D-SIM (determinism/seeds), D-SCH (schema/dtypes/serialisation),
D-RNG (ranges/nonnegativity/mass balance), D-EDGE (tiny/constant/singular), D-OUT (labelling),
D-DES (design integrity), D-GRD (gradients/behaviour of the underlying surfaces).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import config


# --------------------------------------------------------------------------- determinism
def test_same_seed_same_frame() -> None:
    from src.simulate_data import simulate

    a, _ = simulate(seed=11, n_scenarios=25)
    b, _ = simulate(seed=11, n_scenarios=25)
    pd.testing.assert_frame_equal(a, b)


def test_different_seed_changes_values() -> None:
    from src.simulate_data import simulate

    a, _ = simulate(seed=11, n_scenarios=25)
    b, _ = simulate(seed=23, n_scenarios=25)
    assert not np.allclose(a[config.TARGET].to_numpy(), b[config.TARGET].to_numpy())


def test_row_count_is_scenarios_times_replicates() -> None:
    from src.simulate_data import simulate

    frame, latent = simulate(seed=11, n_scenarios=30)
    assert len(frame) == 30 * config.N_REPLICATES
    assert latent["scenario_id"].nunique() == 30
    assert frame["scenario_id"].nunique() == 30


# --------------------------------------------------------------------------- schema
def test_schema_columns_and_order(small_frame: pd.DataFrame) -> None:
    expected = config.FRAME_COLUMNS
    assert list(small_frame.columns) == list(expected)


def test_dtypes_are_float_or_documented(small_frame: pd.DataFrame) -> None:
    for col in small_frame.columns:
        if col in {"scenario_id", "split", "data_provenance", "simulator_version", "as_of"}:
            assert not pd.api.types.is_numeric_dtype(small_frame[col]), col
            assert pd.api.types.is_string_dtype(small_frame[col]), col
        elif col in {"replicate_id", "seed"}:
            assert pd.api.types.is_integer_dtype(small_frame[col]), col
        else:
            assert pd.api.types.is_float_dtype(small_frame[col]), col


def test_simulated_labelling_present(
    small_frame: pd.DataFrame, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert (small_frame["data_provenance"] == "synthetic").all()
    assert (small_frame["simulator_version"] == config.SIMULATOR_VERSION).all()


def test_csv_round_trip(small_frame: pd.DataFrame, tmp_path: Path) -> None:
    from src.simulate_data import write_dataset

    paths = write_dataset(small_frame, pd.DataFrame(), tmp_path, seed=11)
    back = pd.read_csv(paths["frame"])
    assert len(back) == len(small_frame)
    assert list(back.columns) == list(small_frame.columns)
    assert np.allclose(
        back[config.TARGET].to_numpy(dtype=float),
        small_frame[config.TARGET].to_numpy(dtype=float),
    )
    assert paths["metadata"].exists()
    meta = paths["metadata"].read_text(encoding="utf-8")
    assert "SIMULATED" in meta.upper()
    assert "synthetic" in meta


# --------------------------------------------------------------------------- ranges
def test_composition_sums_to_one(small_frame: pd.DataFrame) -> None:
    total = (
        small_frame["carb_fraction"]
        + small_frame["protein_fraction"]
        + small_frame["lipid_fraction"]
    )
    assert np.allclose(total.to_numpy(), 1.0, atol=1e-9)


def test_all_inputs_inside_declared_ranges(small_frame: pd.DataFrame) -> None:
    for name, (low, high) in config.INPUT_RANGES.items():
        col = small_frame[name]
        assert col.min() >= low - 1e-9, name
        assert col.max() <= high + 1e-9, name


def test_outputs_are_nonnegative_and_bounded(small_frame: pd.DataFrame) -> None:
    y = small_frame[config.TARGET]
    assert y.min() >= config.YIELD_MIN
    assert y.max() <= config.YIELD_MAX
    assert small_frame["simulated_biogas_yield_ml_per_g_vs"].min() >= 0.0
    frac = small_frame["simulated_methane_fraction"]
    assert frac.between(0.45, 0.75).all()
    stability = small_frame["simulated_stability_indicator"]
    assert stability.between(0.0, 1.0).all()


def test_mass_balance_between_outputs(small_frame: pd.DataFrame) -> None:
    """biogas * methane_fraction == methane yield (to rounding tolerance)."""
    recomputed = (
        small_frame["simulated_biogas_yield_ml_per_g_vs"]
        * small_frame["simulated_methane_fraction"]
    )
    assert np.allclose(
        recomputed.to_numpy(), small_frame[config.TARGET].to_numpy(), atol=0.2
    )


def test_diagnostic_concentrations_are_nonnegative(small_frame: pd.DataFrame) -> None:
    for col in ("c_lcfa_g_per_l", "tan_g_per_l", "rate_constant_per_day", "window_completeness"):
        assert small_frame[col].min() >= 0.0, col
    assert small_frame["window_completeness"].between(0.0, 1.0).all()


# --------------------------------------------------------------------------- missingness
def test_missingness_is_present_and_small(small_frame: pd.DataFrame) -> None:
    ph_missing = small_frame["ph_measured"].isna().mean()
    t_missing = small_frame["temperature_c"].isna().mean()
    assert 0.0 < ph_missing < 0.06
    assert 0.0 < t_missing < 0.05
    assert abs(ph_missing - config.MISSING_RATE_PH) < 0.02
    assert abs(t_missing - config.MISSING_RATE_TEMP) < 0.02


def test_setpoint_never_missing(small_frame: pd.DataFrame) -> None:
    assert small_frame["ph_setpoint"].notna().all()
    assert small_frame[config.TARGET].notna().all()


# --------------------------------------------------------------------------- edge cases
def test_tiny_dataset_is_supported() -> None:
    from src.simulate_data import simulate

    frame, latent = simulate(seed=11, n_scenarios=3)
    assert len(frame) == 3 * config.N_REPLICATES
    assert len(latent) == 3


@pytest.mark.parametrize("bad", [0, -1])
def test_invalid_scenario_count_raises(bad: int) -> None:
    from src.simulate_data import simulate

    with pytest.raises(ValueError):
        simulate(seed=11, n_scenarios=bad)


def test_wrong_type_seed_raises() -> None:
    from src.simulate_data import simulate

    with pytest.raises(TypeError):
        simulate(seed=11.5, n_scenarios=5)  # type: ignore[arg-type]


def test_negative_pretreatment_hours_raise() -> None:
    from src.simulate_data import pretreatment_progress

    with pytest.raises(ValueError):
        pretreatment_progress(-1.0)


def test_composition_sampler_guard_raises_on_a_small_pool() -> None:
    from src.simulate_data import _sample_composition

    with pytest.raises(RuntimeError):
        _sample_composition(np.random.default_rng(7), 5000, pool_factor=1.0)


def test_wrong_type_scenario_count_raises() -> None:
    from src.simulate_data import simulate

    with pytest.raises(TypeError):
        simulate(seed=11, n_scenarios="many")  # type: ignore[arg-type]


def test_latent_factors_are_not_in_the_model_facing_frame(small_frame: pd.DataFrame) -> None:
    for col in config.LATENT_COLUMNS:
        assert col not in small_frame.columns


def test_latent_frame_has_expected_range() -> None:
    from src.simulate_data import simulate

    _, latent = simulate(seed=11, n_scenarios=40)
    assert latent["pretreatment_response"].between(0.70, 1.60).all()
    assert latent["degradable_mass_loss"].between(0.0, 0.20).all()


# --------------------------------------------------------------------------- design integrity (R-E2 / D-DES-01)
def _pairwise_correlations(per_scenario: pd.DataFrame, columns: tuple[str, ...]) -> dict:
    out = {}
    for i, a in enumerate(columns):
        for b in columns[i + 1 :]:
            out[(a, b)] = abs(float(np.corrcoef(per_scenario[a], per_scenario[b])[0, 1]))
    return out


def test_design_variables_are_structurally_independent() -> None:
    """SPEC_V1 3.2: sampled decision variables carry no correlation beyond composition."""
    from src.simulate_data import simulate

    frame, _ = simulate(seed=11, n_scenarios=250)
    per = frame.groupby("scenario_id", as_index=False).first()
    comp = {"carb_fraction", "protein_fraction", "lipid_fraction"}
    design = tuple(v for v in config.FEATURES if v not in comp and v != "ph_measured")
    worst_pair, worst = max(
        _pairwise_correlations(per, design).items(), key=lambda kv: kv[1]
    )
    assert worst <= 0.20, f"unexpected structural correlation {worst:.3f} in {worst_pair}"


def test_derived_correlations_are_documented_not_silent() -> None:
    """`ph_measured` is derived in the DGP, so it may carry intended dependence on loading.

    Any such dependence above the design threshold must be declared in
    `config.DERIVED_CORRELATION_NOTES` - it may not appear by accident.
    """
    from src.simulate_data import simulate

    frame, _ = simulate(seed=11, n_scenarios=250)
    per = frame.groupby("scenario_id", as_index=False).first()
    derived = ("ph_measured",)
    comp = {"carb_fraction", "protein_fraction", "lipid_fraction"}
    others = tuple(v for v in config.FEATURES if v not in derived and v not in comp)
    flagged = {
        pair: r for pair, r in _pairwise_correlations(per, derived + others).items() if r > 0.20
    }
    for (a, b), r in flagged.items():
        key_a = f"{a}|{b}"
        key_b = f"{b}|{a}"
        assert key_a in config.DERIVED_CORRELATION_NOTES or key_b in config.DERIVED_CORRELATION_NOTES, (
            f"undocumented derived correlation {key_a} = {r:.3f}"
        )


def test_composition_collinearity_is_documented_not_hidden() -> None:
    """The design check found r(p,l) ~ -0.55. It must stay in the documented band."""
    from src.simulate_data import simulate

    frame, _ = simulate(seed=11, n_scenarios=250)
    per = frame.groupby("scenario_id", as_index=False).first()
    r_pl = float(np.corrcoef(per["protein_fraction"], per["lipid_fraction"])[0, 1])
    assert -0.85 < r_pl < -0.25


# --------------------------------------------------------------------------- surfaces (pure functions)
def test_ceiling_increases_with_lipid() -> None:
    from src.simulate_data import ceiling_ml_per_g_vs

    low = ceiling_ml_per_g_vs(np.array([0.70]), np.array([0.20]), np.array([0.10]))
    high = ceiling_ml_per_g_vs(np.array([0.50]), np.array([0.20]), np.array([0.30]))
    assert high[0] > low[0]


def test_ceiling_matches_hand_arithmetic() -> None:
    from src.simulate_data import ceiling_ml_per_g_vs

    got = ceiling_ml_per_g_vs(np.array([0.77]), np.array([0.15]), np.array([0.08]))[0]
    expected = config.BETA * (0.77 * config.K_CARB + 0.15 * config.K_PROT + 0.08 * config.K_LIP) * 1000
    assert got == pytest.approx(expected, rel=1e-12)


def test_temperature_has_two_optima() -> None:
    from src.simulate_data import f_temperature

    assert f_temperature(np.array([33.5]))[0] == pytest.approx(1.0)
    assert f_temperature(np.array([55.0]))[0] == pytest.approx(0.98)
    assert f_temperature(np.array([45.0]))[0] < 0.6


def test_ph_plateau_and_penalty() -> None:
    from src.simulate_data import f_ph

    for value in (6.8, 7.0, 7.2):
        assert f_ph(np.array([value]))[0] == pytest.approx(1.0)
    assert f_ph(np.array([6.0]))[0] < 0.5
    assert f_ph(np.array([8.5]))[0] < 0.3


def test_ph_is_not_penalised_inside_the_plateau() -> None:
    from src.simulate_data import f_ph

    vals = f_ph(np.array([6.8, 6.9, 7.0, 7.1, 7.2]))
    assert np.allclose(vals, 1.0)


def test_pre_treatment_progress_is_zero_at_zero_and_saturates() -> None:
    from src.simulate_data import pretreatment_progress

    assert pretreatment_progress(0.0) == pytest.approx(0.0)
    assert pretreatment_progress(96.0) > 0.9
    assert pretreatment_progress(96.0) < 1.0


def test_availability_and_loss_are_signed_and_bounded() -> None:
    from src.simulate_data import availability_factor, loss_fraction, pretreatment_progress

    g = pretreatment_progress(96.0)
    assert availability_factor(np.array([1.30]), g)[0] > 1.0
    assert availability_factor(np.array([0.75]), g)[0] < 1.0
    assert availability_factor(np.array([1.00]), g)[0] == pytest.approx(1.0)
    assert 0.0 <= loss_fraction(np.array([0.20]), g)[0] <= 0.20


def test_inhibitors_reduce_with_distance_from_threshold() -> None:
    from src.simulate_data import f_lcfa, f_tan

    assert f_lcfa(np.array([0.1]), 1.2)[0] > f_lcfa(np.array([1.2]), 1.2)[0]
    assert f_tan(np.array([1.0]), 6.0)[0] > f_tan(np.array([6.0]), 6.0)[0]
    assert f_lcfa(np.array([1.2]), 1.2)[0] == pytest.approx(0.5)
    assert f_tan(np.array([6.0]), 6.0)[0] == pytest.approx(0.5)


def test_vfa_stress_is_bounded_and_increases_with_loading() -> None:
    from src.simulate_data import vfa_stress

    low = vfa_stress(np.array([0.5]), np.array([0.02]), np.array([0.05]))[0]
    mid = vfa_stress(np.array([2.5]), np.array([0.10]), np.array([0.15]))[0]
    high = vfa_stress(np.array([6.0]), np.array([0.30]), np.array([0.25]))[0]
    assert 0.0 <= low <= mid <= high <= 1.0
    assert low == pytest.approx(0.0)
    assert high == pytest.approx(1.0)


def test_washout_collapses_below_the_threshold() -> None:
    from src.simulate_data import washout_factor

    assert washout_factor(np.array([5.0]))[0] == 0.0
    assert washout_factor(np.array([12.0]))[0] == pytest.approx(1.0)
    assert 0.0 < washout_factor(np.array([9.0]))[0] < 1.0


def test_yield_reference_configuration_matches_the_frozen_anchor() -> None:
    """SPEC_V1 4.1: the reference configuration is an anchor, not a coincidence."""
    from src.simulate_data import yield_endpoint

    got = yield_endpoint(
        carb=np.array([0.77]),
        protein=np.array([0.15]),
        lipid=np.array([0.08]),
        total_solids=np.array([12.0]),
        temperature=np.array([33.5]),
        ph=np.array([7.0]),
        olr=np.array([2.5]),
        hrt=np.array([30.0]),
        inoculum=np.array([4.0]),
        pretreatment_hours=np.array([0.0]),
        pretreatment_response=np.array([1.0]),
        degradable_mass_loss=np.array([0.0]),
    )[0]
    assert got == pytest.approx(411.6, abs=1.0)


def test_yield_is_deterministic_for_fixed_inputs() -> None:
    from src.simulate_data import yield_endpoint

    args = dict(
        carb=np.array([0.70]),
        protein=np.array([0.20]),
        lipid=np.array([0.10]),
        total_solids=np.array([12.0]),
        temperature=np.array([35.0]),
        ph=np.array([7.0]),
        olr=np.array([2.5]),
        hrt=np.array([30.0]),
        inoculum=np.array([2.0]),
        pretreatment_hours=np.array([0.0]),
        pretreatment_response=np.array([1.0]),
        degradable_mass_loss=np.array([0.0]),
    )
    assert yield_endpoint(**args)[0] == yield_endpoint(**args)[0]


# --------------------------------------------------------------------------- validation helper
def test_inoculum_ratio_is_a_flat_descriptor() -> None:
    """SPEC_V1 13.1: I:S is a flat descriptor, so it must not change the yield.

    Regression for A3-C3: an earlier implementation multiplied the yield by a diminishing-returns
    inoculum factor. That contradicted the frozen equation of section 3.3 and made the simulator
    easier than declared - the section 4.1 anchors reproduce only without it. See
    `docs/known_issues.md`.
    """
    from src.simulate_data import simulate, yield_endpoint

    def run(inoculum: float) -> float:
        return float(
            yield_endpoint(
                carb=np.array([0.70]),
                protein=np.array([0.20]),
                lipid=np.array([0.10]),
                total_solids=np.array([12.0]),
                temperature=np.array([35.0]),
                ph=np.array([7.0]),
                olr=np.array([2.5]),
                hrt=np.array([30.0]),
                inoculum=np.array([inoculum]),
                pretreatment_hours=np.array([0.0]),
                pretreatment_response=np.array([1.0]),
                degradable_mass_loss=np.array([0.0]),
            )[0]
        )

    assert run(0.5) == run(2.0) == run(4.0)
    frame, _ = simulate(seed=11, n_scenarios=12)
    assert frame["inoculum_ratio"].nunique() > 5, "the column must still exist as a recorded setting"


def test_validate_frame_accepts_good_data(small_frame: pd.DataFrame) -> None:
    from src.simulate_data import validate_frame

    report = validate_frame(small_frame)
    assert report["ok"] is True
    assert report["checks_failed"] == []


def test_validate_frame_flags_out_of_range(small_frame: pd.DataFrame) -> None:
    from src.simulate_data import validate_frame

    broken = small_frame.copy()
    broken.loc[broken.index[0], "total_solids_pct"] = 99.0
    report = validate_frame(broken)
    assert report["ok"] is False
    assert any("total_solids_pct" in c for c in report["checks_failed"])


def test_validate_frame_flags_mass_balance_breach(small_frame: pd.DataFrame) -> None:
    from src.simulate_data import validate_frame

    broken = small_frame.copy()
    broken.loc[broken.index[0], config.TARGET] = 500.0  # breaks biogas*fraction == yield
    report = validate_frame(broken)
    assert report["ok"] is False


def test_validate_frame_rejects_empty_and_wrong_types() -> None:
    from src.simulate_data import validate_frame

    with pytest.raises(ValueError):
        validate_frame(pd.DataFrame())
    with pytest.raises(TypeError):
        validate_frame([1, 2, 3])  # type: ignore[arg-type]


def test_validate_frame_rejects_infinities(small_frame: pd.DataFrame) -> None:
    from src.simulate_data import validate_frame

    broken = small_frame.copy()
    broken.loc[broken.index[0], "temperature_c"] = np.inf
    report = validate_frame(broken)
    assert report["ok"] is False


def test_the_latent_table_is_labelled_like_the_model_facing_table(tmp_path: Path) -> None:
    """The latent file is published too, so it must not be the one artefact without a marker."""
    from src.simulate_data import simulate, write_dataset

    frame, latent = simulate(seed=11, n_scenarios=12)
    paths = write_dataset(frame, latent, tmp_path, seed=11)
    written = pd.read_csv(paths["latent"])
    assert (written["data_provenance"] == config.DATA_PROVENANCE).all()
    assert (written["simulator_version"] == config.SIMULATOR_VERSION).all()
    assert set(latent.columns) <= set(written.columns)
