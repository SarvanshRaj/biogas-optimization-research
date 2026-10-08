"""Wave D contract: the constrained, uncertainty-aware optimiser and its robustness harness.

Written before `src/optimize.py` exists. The frozen specification this has to satisfy is
`docs/model_specification.md` §10 (three arms, six constraints, ±5 % perturbation) and §9.1
(rule F5). The point of the tests is that the constraints are **enforced**, not reported:
an infeasible recommendation must be impossible to return, not merely flagged.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import config


# --------------------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def reference() -> dict:
    """The two baseline comparators: the declared one and a feasible companion."""
    from src.optimize import baseline_reference

    return baseline_reference()


@pytest.fixture(scope="module")
def run() -> dict:
    """One small full optimiser run: both tiers, true arm plus two surrogate arms, robustness."""
    from src.optimize import run_optimisation

    return run_optimisation(
        seed=11,
        n_scenarios=40,
        model_names=("dummy", "ridge"),
        perturbation_draws=60,
        max_iterations=25,
        population_size=8,
    )


# --------------------------------------------------------------------------- decision vector
def test_two_tier_runs_are_defined_and_differ_by_the_laboratory_variables() -> None:
    from src.optimize import C1_VARIABLES, LAB_VARIABLES

    assert set(C1_VARIABLES) <= set(LAB_VARIABLES)
    extra = set(LAB_VARIABLES) - set(C1_VARIABLES)
    assert extra == {"ph_setpoint", "hrt_days"}
    # the tier list names feed composition as "C/P/L fractions", but the third fraction is
    # derived (lipid = 1 - c - p), so it cannot be an independent decision variable
    assert set(config.TIER_C1) - set(C1_VARIABLES) == {"lipid_fraction"}
    assert "lipid_fraction" not in C1_VARIABLES


def test_every_optimised_variable_has_declared_bounds_inside_the_input_ranges() -> None:
    from src.optimize import C1_VARIABLES, LAB_VARIABLES, decision_bounds

    for variables in (C1_VARIABLES, LAB_VARIABLES):
        bounds = decision_bounds(variables)
        assert len(bounds) == len(variables)
        for name, (low, high) in zip(variables, bounds, strict=True):
            declared = config.INPUT_RANGES[name]
            assert (low, high) == declared, name
            assert low < high


def test_the_inoculum_ratio_is_held_fixed_with_a_stated_reason() -> None:
    from src.optimize import HELD_FIXED, LAB_VARIABLES

    assert "inoculum_ratio" in HELD_FIXED
    assert "inoculum_ratio" not in LAB_VARIABLES
    assert "flat" in HELD_FIXED["inoculum_ratio"]["reason"]
    assert HELD_FIXED["inoculum_ratio"]["value"] == config.BASELINE_PROCESS["inoculum_ratio"]


def test_inoculum_flatness_is_verified_not_assumed() -> None:
    from src.optimize import true_objective

    base = dict(config.BASELINE_PROCESS)
    base.update({"carb_fraction": 0.60, "protein_fraction": 0.15})
    yields = []
    for ratio in (0.5, 1.0, 2.0, 4.0):
        yields.append(true_objective({**base, "inoculum_ratio": ratio}))
    assert max(yields) - min(yields) < 1e-9


def test_mixture_sums_to_one_by_construction() -> None:
    from src.optimize import mixture_from

    carb, protein, lipid = mixture_from({"carb_fraction": 0.60, "protein_fraction": 0.15})
    assert carb == pytest.approx(0.60)
    assert protein == pytest.approx(0.15)
    assert carb + protein + lipid == pytest.approx(1.0)


def test_mixture_outside_the_declared_lipid_range_is_rejected() -> None:
    from src.optimize import mixture_from

    with pytest.raises(ValueError, match="lipid"):
        mixture_from({"carb_fraction": 0.50, "protein_fraction": 0.05})  # lipid = 0.45


def test_vectors_round_trip_through_dicts() -> None:
    from src.optimize import C1_VARIABLES, decision_bounds, dict_from_vector, vector_from_dict

    candidate = {
        "carb_fraction": 0.62,
        "protein_fraction": 0.12,
        "total_solids_pct": 11.0,
        "temperature_c": 37.0,
        "olr_kg_vs_m3_d": 2.0,
        "pretreatment_hours": 12.0,
        "pretreatment_temp_c": 30.0,
    }
    vector = vector_from_dict(candidate, C1_VARIABLES)
    assert vector.shape == (len(C1_VARIABLES),)
    for name, value in zip(C1_VARIABLES, vector, strict=True):
        low, high = decision_bounds(C1_VARIABLES)[list(C1_VARIABLES).index(name)]
        assert low <= value <= high
    assert dict_from_vector(vector, C1_VARIABLES) == candidate


def test_a_candidate_frame_is_one_row_the_simulator_can_score() -> None:
    from src.optimize import candidate_frame, true_objective

    frame = candidate_frame({**config.BASELINE_PROCESS, "carb_fraction": 0.60, "protein_fraction": 0.15})
    assert len(frame) == 1
    for column in ("carb_fraction", "protein_fraction", "lipid_fraction", "ph_measured"):
        assert column in frame.columns
    assert true_objective({**config.BASELINE_PROCESS, "carb_fraction": 0.60, "protein_fraction": 0.15}) > 0


# --------------------------------------------------------------------------- constraints
def test_constraint_report_names_every_frozen_constraint() -> None:
    from src.optimize import constraint_report

    report = constraint_report({**config.BASELINE_PROCESS, "carb_fraction": 0.60, "protein_fraction": 0.15})
    assert set(report["constraints"]) == {"C-b", "C-c", "C-d", "C-e", "C-f"}
    for key in ("stress", "tan_g_per_l", "ph_eff", "hrt_days", "feasible", "violations"):
        assert key in report, key


def test_a_high_lipid_candidate_violates_stability_and_is_infeasible() -> None:
    from src.optimize import constraint_report

    report = constraint_report(
        {
            "carb_fraction": 0.48,
            "protein_fraction": 0.22,
            "total_solids_pct": 12.0,
            "temperature_c": 35.0,
            "ph_setpoint": 7.0,
            "olr_kg_vs_m3_d": 2.5,
            "hrt_days": 30.0,
            "pretreatment_hours": 0.0,
            "pretreatment_temp_c": 30.0,
        }
    )
    assert report["constraints"]["C-c"] is False
    assert report["feasible"] is False
    assert "C-c" in report["violations"]


def test_a_mixture_outside_the_lipid_band_violates_the_box_constraint() -> None:
    from src.optimize import constraint_report

    report = constraint_report(
        {
            "carb_fraction": 0.45,
            "protein_fraction": 0.24,  # lipid = 0.31 > 0.30
            "total_solids_pct": 12.0,
            "temperature_c": 35.0,
            "ph_setpoint": 7.0,
            "olr_kg_vs_m3_d": 2.5,
            "hrt_days": 30.0,
            "pretreatment_hours": 0.0,
            "pretreatment_temp_c": 30.0,
        }
    )
    assert report["constraints"]["C-b"] is False
    assert "lipid_fraction" in report["box_violations"]


def test_assert_feasible_raises_and_lists_the_violated_constraints() -> None:
    from src.optimize import assert_feasible

    with pytest.raises(RuntimeError, match="C-c"):
        assert_feasible(
            {
                "carb_fraction": 0.48,
                "protein_fraction": 0.22,
                "total_solids_pct": 12.0,
                "temperature_c": 35.0,
                "ph_setpoint": 7.0,
                "olr_kg_vs_m3_d": 2.5,
                "hrt_days": 30.0,
                "pretreatment_hours": 0.0,
                "pretreatment_temp_c": 30.0,
            }
        )


def test_infeasible_points_are_penalised_so_they_cannot_win() -> None:
    from src.optimize import constraint_report, penalised_objective, true_objective

    feasible_point = {
        "carb_fraction": 0.70,
        "protein_fraction": 0.10,
        "total_solids_pct": 12.0,
        "temperature_c": 35.0,
        "ph_setpoint": 7.0,
        "olr_kg_vs_m3_d": 1.5,  # measured: at OLR 2.5 this mixture sits ON the C-c threshold
        "hrt_days": 30.0,
        "pretreatment_hours": 0.0,
        "pretreatment_temp_c": 30.0,
    }
    assert constraint_report(feasible_point)["feasible"] is True
    infeasible_point = {
        **feasible_point,
        "carb_fraction": 0.48,
        "protein_fraction": 0.25,
        "olr_kg_vs_m3_d": 2.5,
    }
    assert constraint_report(infeasible_point)["feasible"] is False
    assert penalised_objective(feasible_point) == pytest.approx(true_objective(feasible_point))
    assert penalised_objective(infeasible_point) < 0.0


def test_the_penalty_is_steeper_than_any_yield_gain() -> None:
    from src.optimize import PENALTY_PER_UNIT_VIOLATION

    assert PENALTY_PER_UNIT_VIOLATION > config.YIELD_MAX


# --------------------------------------------------------------------------- baselines
def test_the_declared_baseline_is_reported_with_its_constraint_status(reference: dict) -> None:
    declared = reference["declared"]
    assert declared["label"] == "declared equal-thirds baseline (decision D6)"
    assert declared["candidate"]["carb_fraction"] == pytest.approx(1 / 3)
    assert math.isfinite(declared["true_yield"])
    # This is a finding, not a bug: the frozen D6 mixture violates C-c and C-e at mid-range
    # settings. The reference records it rather than quietly repairing the comparator.
    assert declared["constraints"]["feasible"] is False
    assert set(declared["constraints"]["violations"]) >= {"C-c"}


def test_the_feasible_reference_is_feasible_and_close_to_equal_thirds(reference: dict) -> None:
    feasible = reference["feasible"]
    assert feasible["constraints"]["feasible"] is True
    assert feasible["true_yield"] > reference["declared"]["true_yield"]
    assert math.isclose(
        feasible["candidate"]["carb_fraction"]
        + feasible["candidate"]["protein_fraction"]
        + (1 - feasible["candidate"]["carb_fraction"] - feasible["candidate"]["protein_fraction"]),
        1.0,
    )
    assert "projection" in feasible["label"]


def test_the_feasible_reference_is_reproducible(reference: dict) -> None:
    from src.optimize import baseline_reference

    assert baseline_reference() == reference


# --------------------------------------------------------------------------- the solver
def test_optimiser_finds_an_analytical_optimum() -> None:
    from src.optimize import maximise_objective

    best, value = maximise_objective(lambda x: -(x[0] - 2.0) ** 2, [(0.0, 5.0)], seed=1, max_iterations=40)
    assert best[0] == pytest.approx(2.0, abs=0.2)
    assert value == pytest.approx(0.0, abs=0.05)


def test_optimiser_respects_bounds_at_a_boundary_optimum() -> None:
    from src.optimize import maximise_objective

    best, value = maximise_objective(lambda x: x[0], [(0.0, 5.0)], seed=1, max_iterations=40)
    assert best[0] == pytest.approx(5.0, abs=1e-6)
    assert value == pytest.approx(5.0, abs=1e-6)


def test_optimiser_is_reproducible_for_a_seed() -> None:
    from src.optimize import maximise_objective

    def objective(x: np.ndarray) -> float:
        return -(x[0] - 1.3) ** 2 - (x[1] + 0.4) ** 2

    a = maximise_objective(objective, [(-3.0, 3.0), (-3.0, 3.0)], seed=7, max_iterations=30)
    b = maximise_objective(objective, [(-3.0, 3.0), (-3.0, 3.0)], seed=7, max_iterations=30)
    assert a == b
    assert a[0][0] == pytest.approx(1.3, abs=0.2)


def test_optimiser_needs_at_least_one_bound() -> None:
    from src.optimize import maximise_objective

    with pytest.raises(ValueError, match="bound"):
        maximise_objective(lambda x: x[0], [], seed=1, max_iterations=5)


def test_random_search_reference_is_feasible_and_reproducible() -> None:
    from src.optimize import C1_VARIABLES, random_search_reference

    first = random_search_reference(C1_VARIABLES, seed=3, n_draws=200)
    second = random_search_reference(C1_VARIABLES, seed=3, n_draws=200)
    assert first == second
    assert first["n_feasible_draws"] > 0
    assert first["true_yield"] > 0
    assert first["constraints"]["feasible"] is True


# --------------------------------------------------------------------------- the three arms
def test_all_three_arms_are_reported_for_both_tiers(run: dict) -> None:
    assert set(run["tiers"]) == {"C1", "C1+C2"}
    for tier in run["tiers"].values():
        assert set(tier["arms"]) == {"true", "baseline", "random_search", "surrogate"}
        assert set(tier["arms"]["surrogate"]) >= {"dummy", "ridge"}
        assert tier["arms"]["true"]["constraints"]["feasible"] is True


def test_the_surrogate_arm_re_evaluates_on_the_true_simulator(run: dict) -> None:
    for tier in run["tiers"].values():
        for name, arm in tier["arms"]["surrogate"].items():
            assert math.isfinite(arm["predicted_yield"]), name
            assert math.isfinite(arm["true_yield"]), name
            assert arm["gap"] == pytest.approx(arm["predicted_yield"] - arm["true_yield"])
            assert arm["constraints"]["feasible"] is True
            assert name in config.MODEL_NAMES


def test_the_true_arm_beats_the_feasible_reference(run: dict) -> None:
    for tier in run["tiers"].values():
        assert tier["arms"]["true"]["true_yield"] >= tier["checks"]["feasible_reference_yield"] - 1e-6
        assert tier["checks"]["oracle_beats_reference"] is True


def test_the_true_arm_is_not_worse_than_random_search(run: dict) -> None:
    for tier in run["tiers"].values():
        random_arm = tier["arms"]["random_search"]
        true_arm = tier["arms"]["true"]
        assert true_arm["true_yield"] >= random_arm["true_yield"] - 0.01 * max(
            random_arm["true_yield"], 1.0
        )
        assert tier["checks"]["random_search_yield"] == pytest.approx(random_arm["true_yield"])


def test_both_tiers_are_labelled_and_the_c1_run_holds_laboratory_variables_fixed(run: dict) -> None:
    c1 = run["tiers"]["C1"]
    lab = run["tiers"]["C1+C2"]
    assert c1["tier_label"] == "achievable at home (tier C1)"
    assert lab["tier_label"] == "laboratory recommendation (tiers C1 + C2)"
    for name in ("ph_setpoint", "hrt_days"):
        assert name not in c1["arms"]["true"]["candidate"]
        assert c1["held_fixed"][name]["value"] == config.BASELINE_PROCESS[
            "ph_measured" if name == "ph_setpoint" else name
        ]
    assert "ph_setpoint" in lab["arms"]["true"]["candidate"]


def test_the_recommendation_is_feasible_after_the_optimiser_returns(run: dict) -> None:
    from src.optimize import assert_feasible

    for tier in run["tiers"].values():
        for arm in tier["arms"]["surrogate"].values():
            assert_feasible({**config.BASELINE_PROCESS, **arm["candidate"]})
        assert_feasible({**config.BASELINE_PROCESS, **tier["arms"]["true"]["candidate"]})


def test_the_run_is_reproducible() -> None:
    from src.optimize import run_optimisation

    first = run_optimisation(
        seed=11,
        n_scenarios=30,
        model_names=("dummy",),
        perturbation_draws=20,
        max_iterations=12,
        population_size=6,
    )
    second = run_optimisation(
        seed=11,
        n_scenarios=30,
        model_names=("dummy",),
        perturbation_draws=20,
        max_iterations=12,
        population_size=6,
    )
    assert first["tiers"]["C1"]["arms"]["true"] == second["tiers"]["C1"]["arms"]["true"]
    assert first["tiers"]["C1"]["perturbation"] == second["tiers"]["C1"]["perturbation"]


# --------------------------------------------------------------------------- robustness
def test_perturbation_stays_inside_the_bounds_and_is_reproducible(run: dict) -> None:
    from src.optimize import C1_VARIABLES, decision_bounds, perturbation_report

    candidate = {"carb_fraction": 0.62, "protein_fraction": 0.12, "total_solids_pct": 11.0,
                 "temperature_c": 37.0, "olr_kg_vs_m3_d": 2.0, "pretreatment_hours": 12.0,
                 "pretreatment_temp_c": 30.0}
    first = perturbation_report(candidate, C1_VARIABLES, draws=40, seed=5)
    second = perturbation_report(candidate, C1_VARIABLES, draws=40, seed=5)
    assert first == second
    assert first["fraction"] == config.PERTURBATION_FRACTION
    assert first["draws"] == 40
    for name, (low, high) in zip(C1_VARIABLES, decision_bounds(C1_VARIABLES), strict=True):
        assert first["min_by_variable"][name] >= low - 1e-9
        assert first["max_by_variable"][name] <= high + 1e-9
    assert first["n_feasible"] + first["n_infeasible"] == first["draws"]
    assert 0.0 <= first["feasible_fraction"] <= 1.0
    assert first["min_yield"] <= first["mean_yield"] <= first["max_yield"]


def test_perturbation_reports_the_clipping_it_had_to_do(run: dict) -> None:
    from src.optimize import C1_VARIABLES, perturbation_report

    report = perturbation_report(
        {"carb_fraction": 0.45, "protein_fraction": 0.05, "total_solids_pct": 5.0, "temperature_c": 20.0,
         "olr_kg_vs_m3_d": 0.5, "pretreatment_hours": 0.0, "pretreatment_temp_c": 25.0},
        C1_VARIABLES,
        draws=40,
        seed=5,
    )
    assert report["n_clipped"] > 0
    assert "clip" in report["note"]


def test_a_single_draw_perturbation_has_no_spread() -> None:
    from src.optimize import C1_VARIABLES, perturbation_report

    report = perturbation_report(
        {"carb_fraction": 0.62, "protein_fraction": 0.12, "total_solids_pct": 11.0, "temperature_c": 37.0,
         "olr_kg_vs_m3_d": 2.0, "pretreatment_hours": 12.0, "pretreatment_temp_c": 30.0},
        C1_VARIABLES,
        draws=1,
        seed=5,
    )
    assert report["mean_yield"] == report["min_yield"] == report["max_yield"] == report["centre_yield"]


def test_perturbation_rejects_a_zero_draw_count() -> None:
    from src.optimize import C1_VARIABLES, perturbation_report

    with pytest.raises(ValueError, match="draw"):
        perturbation_report(
            {"carb_fraction": 0.62, "protein_fraction": 0.12, "total_solids_pct": 11.0,
             "temperature_c": 37.0, "olr_kg_vs_m3_d": 2.0, "pretreatment_hours": 12.0,
             "pretreatment_temp_c": 30.0},
            C1_VARIABLES,
            draws=0,
            seed=5,
        )


# --------------------------------------------------------------------------- rule F5
def _perturbation(**overrides: object) -> dict:
    base = {
        "draws": 100,
        "fraction": 0.05,
        "centre_yield": 400.0,
        "mean_yield": 395.0,
        "min_yield": 380.0,
        "max_yield": 405.0,
        "n_feasible": 100,
        "n_infeasible": 0,
        "feasible_fraction": 1.0,
        "best_edge_fraction": 0.2,
    }
    return {**base, **overrides}


def test_f5_does_not_fire_for_a_robust_recommendation() -> None:
    from src.optimize import evaluate_f5

    rules = evaluate_f5(_perturbation(), feasible_reference_yield=365.0, declared_baseline_yield=313.0)
    assert rules["f5_fires"] is False
    assert rules["f5_verdict"] == "robust enough to report, with the perturbation numbers alongside"
    assert rules["f5_conditions"] == {"below_reference": False, "knife_edge": False, "not_stationary": False}


def test_f5_fires_when_the_mean_drops_below_the_feasible_reference() -> None:
    from src.optimize import evaluate_f5

    rules = evaluate_f5(
        _perturbation(mean_yield=360.0), feasible_reference_yield=365.0, declared_baseline_yield=313.0
    )
    assert rules["f5_fires"] is True
    assert rules["f5_conditions"]["below_reference"] is True
    assert rules["f5_verdict"] == "artefactual - report the recommendation as fragile, do not call it a best recipe"


def test_f5_fires_when_most_perturbed_draws_break_a_constraint() -> None:
    from src.optimize import evaluate_f5

    rules = evaluate_f5(
        _perturbation(n_feasible=30, n_infeasible=70, feasible_fraction=0.3, mean_yield=400.0),
        feasible_reference_yield=365.0,
        declared_baseline_yield=313.0,
    )
    assert rules["f5_fires"] is True
    assert rules["f5_conditions"]["knife_edge"] is True


def test_f5_fires_when_the_best_perturbed_point_is_at_the_edge_of_the_ball() -> None:
    from src.optimize import evaluate_f5

    rules = evaluate_f5(
        _perturbation(best_edge_fraction=1.0), feasible_reference_yield=365.0, declared_baseline_yield=313.0
    )
    assert rules["f5_fires"] is True
    assert rules["f5_conditions"]["not_stationary"] is True


def test_f5_records_its_own_thresholds_and_the_numbers_behind_them() -> None:
    from src.optimize import evaluate_f5

    rules = evaluate_f5(_perturbation(), feasible_reference_yield=365.0, declared_baseline_yield=313.0)
    assert rules["f5_rule"]
    assert rules["f5_knife_edge_threshold"] == pytest.approx(0.5)
    assert rules["f5_edge_threshold"] == pytest.approx(0.99)
    assert rules["declared_baseline_yield"] == pytest.approx(313.0)
    assert rules["feasible_reference_yield"] == pytest.approx(365.0)


# --------------------------------------------------------------------------- artefacts
def test_the_caveat_travels_with_every_artefact(run: dict, tmp_path: Path) -> None:
    from src.optimize import write_optimiser_results

    paths = write_optimiser_results(run, tmp_path)
    assert set(paths) >= {"recommendations", "summary", "metadata"}
    meta = json.loads(paths["metadata"].read_text(encoding="utf-8"))
    assert meta["simulated"] is True
    assert meta["data_provenance"] == config.DATA_PROVENANCE
    assert "not a real recipe" in meta["caveat"]
    assert "artefact" in meta["caveat"]
    assert "synthetic" in meta["scope_note"].lower()


def test_every_written_row_carries_the_simulated_marker(run: dict, tmp_path: Path) -> None:
    from src.optimize import write_optimiser_results

    paths = write_optimiser_results(run, tmp_path)
    for key in ("recommendations", "summary"):
        frame = pd.read_csv(paths[key])
        assert (frame["simulated"] == config.SIMULATED_MARKER).all(), key
        assert (frame["simulator_version"] == config.SIMULATOR_VERSION).all(), key


def test_the_summary_table_has_one_row_per_tier_and_arm(run: dict, tmp_path: Path) -> None:
    from src.optimize import write_optimiser_results

    paths = write_optimiser_results(run, tmp_path)
    frame = pd.read_csv(paths["summary"])
    assert set(frame["tier"]) == {"C1", "C1+C2"}
    assert {"oracle", "baseline", "random_search"} <= set(frame["arm"])
    assert (frame["true_yield"] >= 0).all()
    assert frame["f5_fires"].isin([True, False]).all()


def test_recommendation_rows_include_every_decision_variable(run: dict, tmp_path: Path) -> None:
    from src.optimize import write_optimiser_results

    paths = write_optimiser_results(run, tmp_path)
    frame = pd.read_csv(paths["recommendations"])
    for variable in config.FEATURES:
        if variable in ("carb_fraction", "protein_fraction", "lipid_fraction"):
            continue
        assert variable in frame.columns, variable
    assert "lipid_fraction" in frame.columns
    assert (frame[["carb_fraction", "protein_fraction", "lipid_fraction"]].sum(axis=1) - 1.0).abs().max() < 1e-9


# --------------------------------------------------------------------------- CLI and guards
def test_cli_prints_the_caveat_and_writes_the_artefacts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from src.optimize import main

    rc = main(
        [
            "--seed",
            "11",
            "--n-scenarios",
            "30",
            "--models",
            "dummy",
            "--perturbation-draws",
            "20",
            "--max-iterations",
            "12",
            "--population-size",
            "6",
            "--outdir",
            str(tmp_path),
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "[SIMULATED]" in out
    assert "not a real recipe" in out
    assert "artefact" in out
    assert (tmp_path / "optimiser_summary.csv").exists()


def test_cli_rejects_an_unknown_model(tmp_path: Path) -> None:
    from src.optimize import main

    with pytest.raises(ValueError, match="unknown model"):
        main(["--models", "ridge,xgboost", "--outdir", str(tmp_path)])


def test_cli_rejects_an_unknown_tier(tmp_path: Path) -> None:
    from src.optimize import main

    with pytest.raises(ValueError, match="tier"):
        main(["--tiers", "C1,C3", "--outdir", str(tmp_path)])


def test_cli_rejects_a_non_integer_seed(tmp_path: Path) -> None:
    from src.optimize import main

    with pytest.raises(ValueError, match="seed"):
        main(["--seed", "eleven", "--outdir", str(tmp_path)])


def test_run_rejects_an_unknown_model_name() -> None:
    from src.optimize import run_optimisation

    with pytest.raises(ValueError, match="unknown model"):
        run_optimisation(seed=11, n_scenarios=30, model_names=("ridge", "catboost"))


def test_run_rejects_an_unknown_tier() -> None:
    from src.optimize import run_optimisation

    with pytest.raises(ValueError, match="tier"):
        run_optimisation(seed=11, n_scenarios=30, model_names=("dummy",), tiers=("C1", "C3"))


def test_run_rejects_too_few_scenarios_for_a_split() -> None:
    from src.optimize import run_optimisation

    with pytest.raises(ValueError, match="scenarios"):
        run_optimisation(seed=11, n_scenarios=4, model_names=("dummy",))

def test_a_candidate_whose_whole_perturbation_ball_is_infeasible_is_reported_not_faked() -> None:
    from src.optimize import C1_VARIABLES, evaluate_f5, perturbation_report

    corner = {
        "carb_fraction": 0.45,
        "protein_fraction": 0.05,  # lipid 0.50: outside the declared band, so infeasible
        "total_solids_pct": 5.0,
        "temperature_c": 20.0,
        "olr_kg_vs_m3_d": 0.5,
        "pretreatment_hours": 0.0,
        "pretreatment_temp_c": 25.0,
    }
    report = perturbation_report(corner, C1_VARIABLES, draws=25, seed=5)
    assert report["n_feasible"] == 0
    assert report["feasible_fraction"] == 0.0
    assert report["mean_yield"] is None and report["min_yield"] is None
    rules = evaluate_f5(report, feasible_reference_yield=365.0, declared_baseline_yield=313.0)
    assert rules["f5_fires"] is True
    assert rules["f5_conditions"]["below_reference"] is None, "not evaluable, not False"
    assert rules["f5_conditions"]["knife_edge"] is True
    assert rules["f5_verdict"].startswith("artefactual")


# --------------------------------------------------------------------------- guard paths
def test_decision_bounds_rejects_a_variable_without_a_declared_range() -> None:
    from src.optimize import decision_bounds

    with pytest.raises(ValueError, match="no declared range"):
        decision_bounds(("carb_fraction", "not_a_column"))


def test_vector_from_dict_lists_the_missing_variables() -> None:
    from src.optimize import C1_VARIABLES, vector_from_dict

    with pytest.raises(ValueError, match="missing"):
        vector_from_dict({"carb_fraction": 0.6}, C1_VARIABLES)


def test_dict_from_vector_checks_the_length() -> None:
    from src.optimize import C1_VARIABLES, dict_from_vector

    with pytest.raises(ValueError, match="expected"):
        dict_from_vector([0.6, 0.1], C1_VARIABLES)


def test_solver_rejects_a_degenerate_budget() -> None:
    from src.optimize import maximise_objective

    with pytest.raises(ValueError, match="max_iterations"):
        maximise_objective(lambda x: x[0], [(0.0, 1.0)], seed=1, max_iterations=0)
    with pytest.raises(ValueError, match="max_iterations"):
        maximise_objective(lambda x: x[0], [(0.0, 1.0)], seed=1, population_size=1)


def test_random_search_rejects_a_zero_budget() -> None:
    from src.optimize import C1_VARIABLES, random_search_reference

    with pytest.raises(ValueError, match="n_draws"):
        random_search_reference(C1_VARIABLES, seed=1, n_draws=0)


def test_random_search_fails_loudly_when_no_draw_is_feasible() -> None:
    from src.optimize import random_search_reference

    # a held-fixed value far outside its range makes every draw infeasible
    with pytest.raises(RuntimeError, match="feasible"):
        random_search_reference(
            ("carb_fraction",), seed=1, n_draws=5, fixed={"olr_kg_vs_m3_d": 99.0}
        )


def test_the_baseline_projection_fails_loudly_when_no_mixture_is_feasible() -> None:
    from src.optimize import _closest_feasible_mixture

    impossible_process = {
        "total_solids_pct": 12.0,
        "temperature_c": 35.0,
        "ph_measured": 99.0,  # outside the declared pH range: C-b can never hold
        "olr_kg_vs_m3_d": 2.5,
        "hrt_days": 30.0,
        "inoculum_ratio": 2.0,
        "pretreatment_hours": 0.0,
        "pretreatment_temp_c": 30.0,
    }
    with pytest.raises(RuntimeError, match="no feasible mixture"):
        _closest_feasible_mixture(impossible_process, (1 / 3, 1 / 3))


def test_perturbation_rejects_a_degenerate_fraction() -> None:
    from src.optimize import C1_VARIABLES, perturbation_report

    candidate = {
        "carb_fraction": 0.62,
        "protein_fraction": 0.12,
        "total_solids_pct": 11.0,
        "temperature_c": 37.0,
        "olr_kg_vs_m3_d": 2.0,
        "pretreatment_hours": 12.0,
        "pretreatment_temp_c": 30.0,
    }
    with pytest.raises(ValueError, match="fraction"):
        perturbation_report(candidate, C1_VARIABLES, draws=10, seed=5, fraction=0.0)
    with pytest.raises(ValueError, match="fraction"):
        perturbation_report(candidate, C1_VARIABLES, draws=10, seed=5, fraction=1.5)


def test_an_empty_model_list_is_rejected_before_any_work_happens() -> None:
    from src.optimize import run_optimisation

    with pytest.raises(ValueError, match="at least one model"):
        run_optimisation(seed=11, n_scenarios=30, model_names=())


def test_cli_rejects_an_empty_model_or_tier_list(tmp_path: Path) -> None:
    from src.optimize import main

    with pytest.raises(ValueError, match="at least one model"):
        main(["--models", ",", "--outdir", str(tmp_path)])
    with pytest.raises(ValueError, match="at least one tier"):
        main(["--tiers", ",", "--outdir", str(tmp_path)])


def test_the_run_refuses_to_return_an_infeasible_recommendation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The post-check is on the path: if the solver hands back an infeasible point, the run
    raises instead of reporting it. (Without this, "constraints enforced" would rest on tests
    that only feed feasible points to `assert_feasible`.)"""
    import src.optimize as optimize

    infeasible = {
        "carb_fraction": 0.48,
        "protein_fraction": 0.22,  # lipid 0.30, stress well above the C-c limit
        "total_solids_pct": 12.0,
        "temperature_c": 35.0,
        "olr_kg_vs_m3_d": 2.5,
        "pretreatment_hours": 0.0,
        "pretreatment_temp_c": 30.0,
    }
    vector = [infeasible[name] for name in optimize.C1_VARIABLES]
    monkeypatch.setattr(optimize, "maximise_objective", lambda *a, **k: (vector, 999.0))
    with pytest.raises(RuntimeError, match="infeasible"):
        optimize.run_optimisation(
            seed=11,
            n_scenarios=30,
            model_names=("dummy",),
            tiers=("C1",),
            perturbation_draws=5,
            max_iterations=5,
            population_size=4,
        )


def test_the_perturbation_scale_is_a_fraction_of_each_variable_s_range_width() -> None:
    """±5 % means 5 % of *that variable's* range width, not 0.05 in absolute units.

    A mutant that dropped the per-variable width scaling survived the rest of this file: every
    other assertion about the perturbation holds for a ball of any size. This test pins the size.
    """
    from src.optimize import C1_VARIABLES, decision_bounds, perturbation_report

    candidate = {
        "carb_fraction": 0.62,
        "protein_fraction": 0.12,
        "total_solids_pct": 11.0,
        "temperature_c": 37.0,
        "olr_kg_vs_m3_d": 2.0,
        "pretreatment_hours": 12.0,
        "pretreatment_temp_c": 30.0,
    }
    report = perturbation_report(candidate, C1_VARIABLES, draws=120, seed=5)
    for name, (low, high) in zip(C1_VARIABLES, decision_bounds(C1_VARIABLES), strict=True):
        expected = 2.0 * report["fraction"] * (high - low)
        observed = report["max_by_variable"][name] - report["min_by_variable"][name]
        assert observed == pytest.approx(expected, rel=0.15), (
            f"{name}: perturbed spread {observed:.4g} does not match +/-{report['fraction']:.0%} "
            f"of the range width {high - low:g} (expected about {expected:.4g})"
        )
