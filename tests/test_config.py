"""Configuration contract tests (test matrix groups: D-CFG, D-OUT)."""

from __future__ import annotations

import math

import pytest


def test_seeds_are_five_fixed_integers() -> None:
    from src import config

    assert isinstance(config.SEEDS, tuple)
    assert len(config.SEEDS) == 5
    assert all(isinstance(s, int) for s in config.SEEDS)
    assert len(set(config.SEEDS)) == 5


def test_design_sizes_match_the_pre_registration() -> None:
    from src import config

    assert config.N_SCENARIOS * config.N_REPLICATES == 4000
    assert config.N_OOD_SCENARIOS == 60
    assert math.isclose(sum(config.SPLIT_FRACTIONS.values()), 1.0)


def test_target_and_features_disjoint() -> None:
    from src import config

    assert config.TARGET not in config.FEATURES
    assert "split" not in config.FEATURES
    assert "scenario_id" not in config.FEATURES
    assert len(config.FEATURES) == 11


def test_model_set_is_exactly_the_five_specified() -> None:
    from src import config

    assert len(config.MODEL_NAMES) == 5
    assert set(config.MODEL_NAMES) == {
        "dummy",
        "ridge",
        "random_forest",
        "hist_gradient_boosting",
        "mlp",
    }


def test_ranges_are_ordered_and_consistent() -> None:
    from src import config

    for name, (low, high) in config.INPUT_RANGES.items():
        assert low < high, name
    # composition ranges must be able to sum to 1 (feasibility of the simplex)
    c_lo, _ = config.INPUT_RANGES["carb_fraction"]
    p_lo, _ = config.INPUT_RANGES["protein_fraction"]
    l_lo, _ = config.INPUT_RANGES["lipid_fraction"]
    assert c_lo + p_lo + l_lo <= 1.0
    c_hi = config.INPUT_RANGES["carb_fraction"][1]
    p_hi = config.INPUT_RANGES["protein_fraction"][1]
    l_hi = config.INPUT_RANGES["lipid_fraction"][1]
    assert c_hi + p_hi + l_hi > 1.0


def test_ood_ranges_are_outside_the_training_support() -> None:
    from src import config

    tr_lipid_hi = config.INPUT_RANGES["lipid_fraction"][1]
    ood_lipid_lo = config.OOD_RANGES["lipid_fraction"][0]
    assert ood_lipid_lo >= tr_lipid_hi - 1e-9
    tr_ts_hi = config.INPUT_RANGES["total_solids_pct"][1]
    ood_ts_lo = config.OOD_RANGES["total_solids_pct"][0]
    assert ood_ts_lo > tr_ts_hi


def test_ood_central_bands_are_inside_the_training_ranges() -> None:
    """The held-out family may only extend the two declared axes."""
    from src import config

    for column, (low, high) in config.OOD_CENTRAL_BANDS.items():
        reference = config.INPUT_RANGES.get(column, config.SETPOINT_RANGE)
        assert reference[0] <= low < high <= reference[1], column


def test_constraints_are_inside_the_input_ranges() -> None:
    from src import config

    assert config.CONSTRAINTS["hrt_min_days"] >= config.INPUT_RANGES["hrt_days"][0]
    assert config.CONSTRAINTS["ph_min"] >= config.SETPOINT_RANGE[0]
    assert config.CONSTRAINTS["ph_max"] <= config.SETPOINT_RANGE[1]
    assert 0.0 <= config.CONSTRAINTS["stability_max"] <= 1.0


def test_scale_adoption_notes_exist_and_name_the_source() -> None:
    """D-SCH-06: the physical-unit guard rails must be available as constants."""
    from src import config

    assert "SIMULATED" in config.SCALE_ADOPTION_NOTE.upper()
    assert "CIT-0004" in config.SCALE_ADOPTION_NOTE
    note = config.NO_BMP_PROTOCOL_NOTE.lower()
    assert "bmp" in note
    assert "no bmp protocol" in note or "not a bmp" in note


def test_sensitivity_grid_has_ten_items_with_three_levels() -> None:
    from src import config

    assert len(config.SENSITIVITY_GRID) == 10
    for key, levels in config.SENSITIVITY_GRID.items():
        assert len(levels) == 3, key


def test_no_scipy_or_sklearn_import_at_config_level() -> None:
    """config must stay a leaf module: importing it must not pull heavy dependencies."""
    import subprocess
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    code = (
        "import sys; import src.config; "
        "assert 'sklearn' not in sys.modules; assert 'scipy' not in sys.modules"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, cwd=repo_root
    )
    assert out.returncode == 0, out.stderr


def test_generator_constants_are_positive_and_bounded() -> None:
    from src import config

    assert 0.0 < config.BETA <= 1.0
    assert config.K_REF > 0
    assert 0.0 < config.VS_TS <= 1.0
    assert config.C_LCFA_HALF > 0 and config.C_TAN_HALF > 0
    assert 0.0 < config.ETA_LCFA < 1.0
    assert config.PRETREATMENT_TAU_H > 0
    assert config.INPUT_RANGES["pretreatment_hours"][0] == 0.0


def test_missingness_rates_are_small_probabilities() -> None:
    from src import config

    for rate in (config.MISSING_RATE_PH, config.MISSING_RATE_TEMP):
        assert 0.0 < rate < 0.1


@pytest.mark.parametrize("tier", ["C1", "C2"])
def test_decision_tiers_are_subsets_of_features(tier: str) -> None:
    from src import config

    tier_vars = getattr(config, f"TIER_{tier}")
    assert set(tier_vars) <= set(config.FEATURES)
    assert tier_vars  # non-empty


def test_c1_and_c2_are_disjoint_and_cover_the_features() -> None:
    from src import config

    c1, c2 = set(config.TIER_C1), set(config.TIER_C2)
    assert not (c1 & c2)
    assert c1 | c2 == set(config.FEATURES)
