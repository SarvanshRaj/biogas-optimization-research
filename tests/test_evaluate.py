"""Wave C contract: the 5-seed evaluation pipeline, its controls and its artefacts.

Written before `src/evaluate.py` exists, so that the module has to satisfy the frozen
protocol in `docs/model_specification.md` §9 (mean ± spread over five seeds; test split
opened once; held-out family reported separately; feature importance labelled "what the
model used") instead of whatever is convenient to implement.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib
import pandas as pd
import pytest

from src import config

matplotlib.use("Agg")


# --------------------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def evaluation() -> dict:
    """One real evaluation run at a size that keeps the suite fast (3 seeds, 40 scenarios)."""
    from src.evaluate import evaluate_models

    return evaluate_models(seeds=(11, 23, 37), n_scenarios=40, ood_scenarios=12)


# --------------------------------------------------------------------------- shapes
def test_seed_rows_carry_the_declared_fields(evaluation: dict) -> None:
    for row in evaluation["rows"]:
        assert set(row) >= {"seed", "model", "split", "n", "r2", "mae", "rmse", "target_std"}
        assert row["model"] in config.MODEL_NAMES
        assert row["split"] in {"validation", "test"}
        assert row["n"] > 0
        assert math.isfinite(row["mae"]) and math.isfinite(row["rmse"])


def test_every_model_is_evaluated_on_every_seed(evaluation: dict) -> None:
    frame = pd.DataFrame(evaluation["rows"])
    for split in ("validation", "test"):
        counts = frame[frame["split"] == split].groupby("model")["seed"].nunique()
        assert set(counts.index) == set(config.MODEL_NAMES)
        assert set(counts) == {3}


def test_ood_rows_are_separate_and_labelled(evaluation: dict) -> None:
    ood = evaluation["ood_rows"]
    assert ood, "the held-out family must be reported separately, not merged into the test rows"
    for row in ood:
        assert row["split"] == "ood"
        assert row["model"] in config.MODEL_NAMES


def test_ood_is_never_part_of_fitting(evaluation: dict) -> None:
    fitted = evaluation["fitted"]
    splits = evaluation["splits"]
    expected = len(splits["train"]) + len(splits["validation"])
    for name, model in fitted.items():
        assert model.fit_rows == expected, name
    assert "ood" in splits, "the held-out family is carried alongside, never merged"


def test_ood_can_be_switched_off_without_changing_the_rest() -> None:
    from src.evaluate import evaluate_seed

    result = evaluate_seed(11, 40, ood_scenarios=0, names=("dummy",))
    assert result["ood_rows"] == []
    assert result["ood"] is None
    assert [row["model"] for row in result["rows"]] == ["dummy", "dummy"]


# --------------------------------------------------------------------------- summary
def _hand_rows() -> list[dict]:
    return [
        {
            "seed": 1,
            "model": "ridge",
            "split": "test",
            "n": 10,
            "r2": 0.5,
            "mae": 1.0,
            "rmse": 2.0,
            "target_std": 5.0,
        },
        {
            "seed": 2,
            "model": "ridge",
            "split": "test",
            "n": 10,
            "r2": 0.7,
            "mae": 3.0,
            "rmse": 4.0,
            "target_std": 5.0,
        },
    ]


def test_summary_is_hand_checkable() -> None:
    from src.evaluate import summarise_seed_metrics

    summary = {(row["model"], row["split"], row["metric"]): row for row in summarise_seed_metrics(_hand_rows())}
    r2 = summary[("ridge", "test", "r2")]
    assert r2["mean"] == pytest.approx(0.6)
    assert r2["std"] == pytest.approx(0.1 * math.sqrt(2))
    assert r2["minimum"] == pytest.approx(0.5)
    assert r2["maximum"] == pytest.approx(0.7)
    assert r2["n_seeds"] == 2 and r2["n_finite"] == 2
    mae = summary[("ridge", "test", "mae")]
    assert mae["mean"] == pytest.approx(2.0)
    assert mae["std"] == pytest.approx(math.sqrt(2))
    assert set(summary) == {("ridge", "test", m) for m in ("r2", "mae", "rmse")}


def test_summary_reports_how_many_finite_values_it_used() -> None:
    from src.evaluate import summarise_seed_metrics

    rows = _hand_rows()
    rows.append(
        {
            "seed": 3,
            "model": "ridge",
            "split": "test",
            "n": 10,
            "r2": None,
            "mae": 2.0,
            "rmse": 3.0,
            "target_std": 5.0,
        }
    )
    summary = {(row["model"], row["split"], row["metric"]): row for row in summarise_seed_metrics(rows)}
    assert summary[("ridge", "test", "r2")]["n_finite"] == 2
    assert summary[("ridge", "test", "r2")]["n_seeds"] == 3
    assert summary[("ridge", "test", "r2")]["mean"] == pytest.approx(0.6)


def test_summary_is_deterministically_ordered(evaluation: dict) -> None:
    from src.evaluate import summarise_seed_metrics

    a = summarise_seed_metrics(evaluation["rows"])
    b = summarise_seed_metrics(list(reversed(evaluation["rows"])))
    assert a == b


def test_summary_rejects_empty_input() -> None:
    from src.evaluate import summarise_seed_metrics

    with pytest.raises(ValueError, match="no rows"):
        summarise_seed_metrics([])


def test_spread_is_over_seeds_not_rows(evaluation: dict) -> None:
    summary = {(row["model"], row["split"], row["metric"]): row for row in evaluation["summary"]}
    assert summary[("ridge", "test", "r2")]["n_seeds"] == 3


# --------------------------------------------------------------------------- decision rules
def _rule_rows(r2_by_seed: dict[str, dict[int, float]]) -> list[dict]:
    rows = []
    for model, per_seed in r2_by_seed.items():
        for seed, value in per_seed.items():
            rows.append(
                {
                    "seed": seed,
                    "model": model,
                    "split": "test",
                    "n": 100,
                    "r2": value,
                    "mae": 1.0,
                    "rmse": 2.0,
                    "target_std": 10.0,
                }
            )
    return rows


def test_f3_fires_when_ridge_matches_the_trees() -> None:
    from src.evaluate import evaluate_decision_rules

    rows = _rule_rows(
        {
            "dummy": {11: -0.01, 23: 0.00, 37: 0.01},
            "ridge": {11: 0.80, 23: 0.82, 37: 0.81},
            "random_forest": {11: 0.82, 23: 0.84, 37: 0.83},
            "hist_gradient_boosting": {11: 0.81, 23: 0.83, 37: 0.82},
            "mlp": {11: 0.79, 23: 0.81, 37: 0.80},
        }
    )
    rules = evaluate_decision_rules(rows)
    assert rules["f3_fires"] is True
    assert rules["f3_verdict"] == "uninformative - do not report a model ranking"
    assert rules["f3_best_tree"] in {"random_forest", "hist_gradient_boosting"}


def test_f3_does_not_fire_when_ridge_lags_the_trees() -> None:
    from src.evaluate import evaluate_decision_rules

    rows = _rule_rows(
        {
            "dummy": {11: -0.01, 23: 0.00, 37: 0.01},
            "ridge": {11: 0.40, 23: 0.45, 37: 0.42},
            "random_forest": {11: 0.75, 23: 0.78, 37: 0.76},
            "hist_gradient_boosting": {11: 0.80, 23: 0.81, 37: 0.79},
            "mlp": {11: 0.70, 23: 0.72, 37: 0.71},
        }
    )
    rules = evaluate_decision_rules(rows)
    assert rules["f3_fires"] is False
    assert rules["f3_verdict"] == "informative - the nonlinear models earn their place"


def test_f7_fires_when_the_best_model_overlaps_the_dummy_baseline() -> None:
    from src.evaluate import evaluate_decision_rules

    # the best model by mean has one bad seed, so its min-max range reaches down into the
    # dummy baseline's band: that is exactly the situation F7 is written to catch
    rows = _rule_rows(
        {
            "dummy": {11: -0.05, 23: 0.10, 37: 0.02},
            "ridge": {11: 0.20, 23: 0.30, 37: 0.25},
            "random_forest": {11: 0.10, 23: 0.35, 37: 0.15},
            "hist_gradient_boosting": {11: 0.15, 23: 0.40, 37: 0.20},
            "mlp": {11: -0.02, 23: 0.60, 37: 0.55},
        }
    )
    rules = evaluate_decision_rules(rows)
    assert rules["f7_fires"] is True
    assert rules["f7_verdict"] == "seed-dependent - report the overlap, do not claim skill"
    assert rules["f7_best_model"] == "mlp"


def test_f7_does_not_fire_when_the_ranges_are_disjoint() -> None:
    from src.evaluate import evaluate_decision_rules

    rows = _rule_rows(
        {
            "dummy": {11: -0.05, 23: -0.02, 37: 0.00},
            "ridge": {11: 0.50, 23: 0.55, 37: 0.52},
            "random_forest": {11: 0.70, 23: 0.72, 37: 0.71},
            "hist_gradient_boosting": {11: 0.80, 23: 0.82, 37: 0.81},
            "mlp": {11: 0.60, 23: 0.62, 37: 0.61},
        }
    )
    rules = evaluate_decision_rules(rows)
    assert rules["f7_fires"] is False
    assert rules["f7_verdict"] == "stable - the best model clears the baseline's spread"


def test_rules_record_their_own_thresholds() -> None:
    from src.evaluate import evaluate_decision_rules

    rules = evaluate_decision_rules(_hand_rows() + _rule_rows({"dummy": {1: 0.0, 2: 0.0}}))
    assert rules["f3_threshold"] == pytest.approx(0.95)
    assert "mean" in rules["f3_rule"] and "test" in rules["f3_rule"]
    assert rules["f7_rule"]


def test_rules_reject_rows_without_a_dummy_baseline() -> None:
    from src.evaluate import evaluate_decision_rules

    rows = [row for row in _rule_rows({"ridge": {11: 0.5}}) if row["model"] != "dummy"]
    with pytest.raises(ValueError, match="dummy"):
        evaluate_decision_rules(rows)


# --------------------------------------------------------------------------- importance
def test_feature_importance_is_labelled_as_model_usage_not_causation(evaluation: dict) -> None:
    from src.evaluate import feature_importance_table

    table = feature_importance_table(evaluation["fitted"], evaluation["splits"]["test"], seed=11, n_repeats=2)
    frame = pd.DataFrame(table)
    assert set(frame["model"]) == set(config.MODEL_NAMES)
    assert set(frame["feature"]) == set(config.FEATURES)
    assert len(frame) == len(config.MODEL_NAMES) * len(config.FEATURES)
    for label in frame["label"]:
        assert "what the model used" in label
        assert "not" in label and "biology" in label
    assert frame["importance_mean"].apply(math.isfinite).all()


def test_feature_importance_is_reproducible_for_a_fixed_seed(evaluation: dict) -> None:
    from src.evaluate import feature_importance_table

    a = feature_importance_table(evaluation["fitted"], evaluation["splits"]["test"], seed=11, n_repeats=2)
    b = feature_importance_table(evaluation["fitted"], evaluation["splits"]["test"], seed=11, n_repeats=2)
    assert a == b


# --------------------------------------------------------------------------- figures
def test_every_figure_is_stamped_simulated(evaluation: dict) -> None:
    from src.evaluate import (
        build_prediction_figure,
        build_residual_figure,
        build_seed_spread_figure,
    )

    figures = {
        "prediction": build_prediction_figure(
            evaluation["fitted"], evaluation["splits"]["test"], title="predicted vs true"
        ),
        "residual": build_residual_figure(
            evaluation["fitted"], evaluation["splits"]["test"], title="residuals"
        ),
        "seed_spread": build_seed_spread_figure(evaluation["rows"], title="seed spread"),
    }
    for name, fig in figures.items():
        texts = [fig.get_suptitle(), *[text.get_text() for text in fig.texts]]
        blob = " ".join(texts).upper()
        assert "SIMULATED" in blob, name
        assert config.SIMULATOR_VERSION in " ".join(texts), name
        assert len(fig.axes) > 0, name


def test_figures_are_written_as_png(evaluation: dict, tmp_path: Path) -> None:
    from src.evaluate import build_seed_spread_figure, save_figure

    fig = build_seed_spread_figure(evaluation["rows"], title="seed spread")
    path = save_figure(fig, tmp_path / "spread.png")
    assert path.exists()
    assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert path.stat().st_size > 5_000


def test_seed_spread_figure_survives_a_single_seed() -> None:
    from src.evaluate import build_seed_spread_figure

    fig = build_seed_spread_figure(_hand_rows(), title="one seed")
    assert len(fig.axes) >= 1


# --------------------------------------------------------------------------- artefacts
def test_write_results_writes_every_declared_artifact(evaluation: dict, tmp_path: Path) -> None:
    from src.evaluate import write_results

    paths = write_results(evaluation, tmp_path)
    assert set(paths) >= {
        "seed_level",
        "summary",
        "ood",
        "rules",
        "metadata",
        "figures/predicted_vs_true",
        "figures/residuals_vs_predicted",
        "figures/seed_spread",
    }
    for key, path in paths.items():
        assert path.exists(), key


def test_every_csv_row_is_labelled_simulated(evaluation: dict, tmp_path: Path) -> None:
    from src.evaluate import write_results

    paths = write_results(evaluation, tmp_path)
    for key in ("seed_level", "summary"):
        frame = pd.read_csv(paths[key])
        assert (frame["simulated"] == config.SIMULATED_MARKER).all(), key
        assert (frame["simulator_version"] == config.SIMULATOR_VERSION).all(), key


def test_metadata_states_provenance_and_scope(evaluation: dict, tmp_path: Path) -> None:
    from src.evaluate import write_results

    paths = write_results(evaluation, tmp_path)
    meta = json.loads(paths["metadata"].read_text(encoding="utf-8"))
    assert meta["simulated"] is True
    assert meta["data_provenance"] == config.DATA_PROVENANCE
    assert meta["simulator_version"] == config.SIMULATOR_VERSION
    assert meta["seeds"] == [11, 23, 37]
    assert "synthetic" in meta["scope_note"].lower()
    assert "not" in meta["scope_note"].lower()


def test_the_decision_rules_artefact_carries_provenance(evaluation: dict, tmp_path: Path) -> None:
    """Regression for P4-1: the rules JSON was the one results artefact without a provenance
    header, caught by the content guard once results/ existed."""
    from src.evaluate import write_results

    paths = write_results(evaluation, tmp_path)
    rules = json.loads(paths["rules"].read_text(encoding="utf-8"))
    assert rules["simulated"] is True
    assert rules["data_provenance"] == config.DATA_PROVENANCE
    assert rules["simulator_version"] == config.SIMULATOR_VERSION
    assert rules["as_of"] == config.AS_OF


def test_decision_rules_are_written_with_the_numbers_behind_them(
    evaluation: dict, tmp_path: Path
) -> None:
    from src.evaluate import write_results

    paths = write_results(evaluation, tmp_path)
    rules = json.loads(paths["rules"].read_text(encoding="utf-8"))
    assert rules["f3_rule"] and rules["f7_rule"]
    assert "f3_ridge_mean_r2" in rules and "f3_best_tree_mean_r2" in rules
    assert rules["f3_ridge_mean_r2"] is None or math.isfinite(rules["f3_ridge_mean_r2"])
    assert rules["f7_best_model_range"][0] <= rules["f7_best_model_range"][1]


def test_results_are_reproducible_for_the_same_seed() -> None:
    from src.evaluate import evaluate_seed

    a = evaluate_seed(11, 30, names=("dummy", "ridge"))
    b = evaluate_seed(11, 30, names=("dummy", "ridge"))
    assert a["rows"] == b["rows"]


# --------------------------------------------------------------------------- guards
def test_unknown_model_is_rejected() -> None:
    from src.evaluate import evaluate_seed

    with pytest.raises(ValueError, match="unknown model"):
        evaluate_seed(11, 30, names=("ridge", "xgboost"))


def test_unknown_metric_is_rejected() -> None:
    from src.evaluate import summarise_seed_metrics

    with pytest.raises(ValueError, match="metric"):
        summarise_seed_metrics(_hand_rows(), metrics=("r2", "roc_auc"))


def test_too_few_scenarios_for_a_grouped_split_is_rejected() -> None:
    from src.evaluate import evaluate_seed

    with pytest.raises(ValueError, match="scenarios"):
        evaluate_seed(11, 4, names=("dummy",))


# --------------------------------------------------------------------------- CLI
def test_cli_runs_a_small_end_to_end_evaluation(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from src.evaluate import main

    rc = main(
        [
            "--seeds",
            "11,23",
            "--n-scenarios",
            "30",
            "--ood-scenarios",
            "8",
            "--outdir",
            str(tmp_path),
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert out.count("[SIMULATED]") >= 2
    assert "mean" in out.lower()
    assert (tmp_path / "metrics_summary.csv").exists()
    assert (tmp_path / "figures" / "predicted_vs_true.png").exists()


def test_cli_rejects_a_bad_seed_list(tmp_path: Path) -> None:
    from src.evaluate import main

    with pytest.raises(ValueError, match="seed"):
        main(["--seeds", "11,abc", "--n-scenarios", "30", "--outdir", str(tmp_path)])


def test_cli_rejects_an_unknown_model(tmp_path: Path) -> None:
    from src.evaluate import main

    with pytest.raises(ValueError, match="unknown model"):
        main(["--models", "ridge,xgboost", "--n-scenarios", "30", "--outdir", str(tmp_path)])


def test_negative_ood_count_is_rejected() -> None:
    from src.evaluate import evaluate_seed

    with pytest.raises(ValueError, match="negative"):
        evaluate_seed(11, 30, ood_scenarios=-1, names=("dummy",))


def test_a_single_seed_has_no_spread_to_report() -> None:
    from src.evaluate import summarise_seed_metrics

    summary = summarise_seed_metrics(_hand_rows()[:1])
    row = summary[0]
    assert row["n_seeds"] == 1 and row["n_finite"] == 1
    assert row["std"] is None, "one seed cannot have a spread; 0.0 would look like certainty"
    assert row["mean"] == pytest.approx(0.5)


def test_prediction_figure_marks_an_undefined_r2(evaluation: dict) -> None:
    from src.evaluate import build_prediction_figure

    frame = evaluation["splits"]["test"].copy()
    frame[config.TARGET] = 400.0  # a constant target makes R2 undefined (SS_tot = 0)
    fig = build_prediction_figure(evaluation["fitted"], frame, title="constant target")
    titles = [ax.get_title() for ax in fig.axes]
    assert any("undefined" in title for title in titles)


def test_seed_spread_figure_needs_test_rows() -> None:
    from src.evaluate import build_seed_spread_figure

    validation_only = [{**row, "split": "validation"} for row in _hand_rows()]
    with pytest.raises(ValueError, match="test"):
        build_seed_spread_figure(validation_only, title="no test rows")


def test_evaluation_needs_at_least_one_seed() -> None:
    from src.evaluate import evaluate_models

    with pytest.raises(ValueError, match="seed"):
        evaluate_models(seeds=(), n_scenarios=20, ood_scenarios=0, names=("dummy",))


def test_cli_rejects_an_empty_seed_list(tmp_path: Path) -> None:
    from src.evaluate import main

    with pytest.raises(ValueError, match="seed"):
        main(["--seeds", ",", "--n-scenarios", "20", "--outdir", str(tmp_path)])


def test_decision_rules_need_a_finite_test_row() -> None:
    from src.evaluate import evaluate_decision_rules

    rows = [{**row, "r2": None} for row in _hand_rows()]
    with pytest.raises(ValueError, match="finite test-split"):
        evaluate_decision_rules(rows)


def test_figures_describe_one_named_seed_and_the_tables_cover_all_of_them(
    evaluation: dict,
) -> None:
    assert evaluation["figure_seed"] == 11, "the first seed is the one the figures describe"
    assert {model.seed for model in evaluation["fitted"].values()} == {11}
    assert evaluation["seeds"] == [11, 23, 37]
