"""Constrained optimisation over the simulated surface - SIMULATED data only.

Implements `docs/model_specification.md` §10 (three arms, six constraints, the ±5 %
perturbation protocol) and §9.1 rule F5. The warning that belongs on every number this module
produces is in `CAVEAT`: an optimiser run against a simulator optimises **the simulator**, and
the "best" values it returns are a property of that synthetic surface, not a validated recipe.

Design decisions, all made before any optimisation result existed:

* **Decision vector.** The mixture is parameterised by `carb_fraction` and `protein_fraction`
  with `lipid_fraction = 1 - c - p`, so "the fractions sum to one" holds by construction and
  `lipid_fraction` is *not* an independent variable (SPEC §10). `inoculum_ratio` is a flat
  descriptor in this simulator (SPEC §13.1, RH-13), so optimising it would mean optimising
  nothing; it is held at the baseline value and the flatness is checked by a test rather than
  assumed.
* **Two tier runs.** SPEC §2 freezes two runs - tier C1 ("achievable at home") and tier
  C1 + C2 ("laboratory") - and requires both to be reported with their tier label.
* **Reference latent values.** The true objective is evaluated at the anchor convention used in
  `tests/test_spec_anchors.py`: pre-treatment response 1.00 and degradable-mass loss 0.10. The
  oracle therefore knows something no real operator knows; that advantage is disclosed rather
  than hidden, and it is exactly what makes arm 1 an *oracle* rather than a plan.
* **Constraints are enforced.** Candidate points are scored with a penalty that dwarfs any
  achievable yield, and the returned recommendation is passed through `assert_feasible`, which
  raises instead of reporting. A recommendation that breaks a constraint cannot be returned.
"""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import scipy
from scipy.optimize import differential_evolution

from src import config
from src.simulate_data import (
    ph_effective,
    simulate,
    tan_concentration,
    vfa_stress,
    yield_endpoint,
)
from src.train_models import (
    FittedModel,
    fit_all_models,
    make_feature_frame,
    split_frame,
    transform_features,
)

# --------------------------------------------------------------------------- decision space
#: Tier C1 (operator-controllable) minus the dependent third fraction, which is derived.
C1_VARIABLES: tuple[str, ...] = tuple(
    name for name in config.TIER_C1 if name != "lipid_fraction"
)
#: Tier C2 additions that a decision vector can actually set (pH setpoint, retention time).
LAB_EXTRA: tuple[str, ...] = ("ph_setpoint", "hrt_days")
LAB_VARIABLES: tuple[str, ...] = C1_VARIABLES + LAB_EXTRA
TIER_NAMES: tuple[str, ...] = ("C1", "C1+C2")

#: Variables deliberately *not* optimised, with the reason. `inoculum_ratio` has no term in the
#: frozen yield equation; leaving it free would put an arbitrary number in a "best recipe".
HELD_FIXED: dict[str, dict[str, Any]] = {
    "inoculum_ratio": {
        "value": config.BASELINE_PROCESS["inoculum_ratio"],
        "reason": (
            "flat descriptor: SPEC_V1 13.1 gives the inoculum-to-substrate ratio no term in the "
            "yield equation (RH-13), so it cannot affect the objective. Held at the baseline "
            "value; the flatness is verified by a test, not assumed."
        ),
    },
}
#: Held fixed in the C1-only run because they are tier-C2 (laboratory) quantities.
C1_HELD_FIXED: dict[str, dict[str, Any]] = {
    "ph_setpoint": {
        "value": config.BASELINE_PROCESS["ph_measured"],
        "reason": "tier C2 (laboratory-only): held at the baseline mid-range pH setpoint",
    },
    "hrt_days": {
        "value": config.BASELINE_PROCESS["hrt_days"],
        "reason": "tier C2 (laboratory-only): held at the baseline mid-range retention time",
    },
}

#: The latent values the true objective is evaluated at (anchor convention).
REFERENCE_LATENT: dict[str, float] = {"pretreatment_response": 1.00, "degradable_mass_loss": 0.10}

#: Penalty per unit of normalised constraint violation. Must dwarf any achievable yield, so an
#: infeasible point can never outrank a feasible one.
PENALTY_PER_UNIT_VIOLATION = 10_000.0

#: F5: a recommendation whose perturbed draws are mostly infeasible sits on a knife edge.
F5_KNIFE_EDGE_THRESHOLD = 0.5
#: F5: the best perturbed draw sitting this close to the edge of the ±5 % ball means the
#: recommendation is not a local optimum - small changes move the best point outward.
F5_EDGE_THRESHOLD = 0.99

#: Grid resolution for the feasible baseline projection (deterministic, so reproducible).
BASELINE_GRID_STEP = 0.002

DEFAULT_MAX_ITERATIONS = 60
DEFAULT_POPULATION_SIZE = 15
DEFAULT_PERTURBATION_DRAWS = 200
MIN_SCENARIOS = 10

CAVEAT = (
    "This optimiser maximises a simulator, so it can and will exploit the simulator's "
    "artefacts. The 'best' values below are a property of this synthetic surface; the best "
    "recipe is not a real recipe, has never been tested on real food waste, and is reported "
    "with its perturbation behaviour so that a fragile optimum is visible as such."
)
SCOPE_NOTE = (
    "Objective = simulated_methane_yield_ml_per_g_vs from src/simulate_data.py "
    f"({config.SIMULATOR_VERSION}), evaluated at reference latent values "
    f"(response {REFERENCE_LATENT['pretreatment_response']}, mass loss "
    f"{REFERENCE_LATENT['degradable_mass_loss']}) on synthetic data. Nothing here is a "
    "measurement, a design, or a recommendation for a real digester."
)


# --------------------------------------------------------------------------- candidates
def decision_bounds(variables: tuple[str, ...]) -> list[tuple[float, float]]:
    """The declared range of each optimised variable (SPEC §3.1 / `config.INPUT_RANGES`)."""
    unknown = [name for name in variables if name not in config.INPUT_RANGES]
    if unknown:
        raise ValueError(f"no declared range for {unknown}")
    return [config.INPUT_RANGES[name] for name in variables]


def mixture_from(candidate: dict[str, float]) -> tuple[float, float, float]:
    """Carb / protein / lipid fractions, with the third derived so they sum to one."""
    carb = float(candidate["carb_fraction"])
    protein = float(candidate["protein_fraction"])
    lipid = 1.0 - carb - protein
    low, high = config.INPUT_RANGES["lipid_fraction"]
    if not low - 1e-9 <= lipid <= high + 1e-9:
        raise ValueError(
            f"implied lipid_fraction {lipid:.4f} is outside the declared range [{low}, {high}] "
            f"for carb_fraction={carb} and protein_fraction={protein}"
        )
    return carb, protein, lipid


def full_candidate(candidate: dict[str, float]) -> dict[str, float]:
    """Fill in the variables that were not optimised, using the declared baseline values.

    A candidate that omits the mixture inherits the declared D6 equal-thirds mixture, which
    violates the box constraint on lipid - that is a property of the declared baseline, not a
    silent default, and it is reported as such by `constraint_report`.
    """
    merged: dict[str, float] = {
        "carb_fraction": 1.0 / 3.0,
        "protein_fraction": 1.0 / 3.0,
        **config.BASELINE_PROCESS,
    }
    merged.update({name: float(value) for name, value in candidate.items()})
    baseline_ph = float(config.BASELINE_PROCESS["ph_measured"])
    if "ph_setpoint" not in candidate:
        merged["ph_setpoint"] = float(merged.get("ph_measured", baseline_ph))
    if "ph_measured" not in candidate:
        merged["ph_measured"] = float(merged["ph_setpoint"])
    for name, entry in HELD_FIXED.items():
        merged.setdefault(name, float(entry["value"]))
    return merged


def candidate_frame(candidate: dict[str, float]) -> pd.DataFrame:
    """One row with the columns the simulator's endpoint equation consumes."""
    values = full_candidate(candidate)
    carb, protein, lipid = mixture_from(values)
    row = {
        "carb_fraction": carb,
        "protein_fraction": protein,
        "lipid_fraction": lipid,
        "total_solids_pct": values["total_solids_pct"],
        "temperature_c": values["temperature_c"],
        "ph_setpoint": values["ph_setpoint"],
        "ph_measured": values["ph_measured"],
        "olr_kg_vs_m3_d": values["olr_kg_vs_m3_d"],
        "hrt_days": values["hrt_days"],
        "inoculum_ratio": values["inoculum_ratio"],
        "pretreatment_hours": values["pretreatment_hours"],
        "pretreatment_temp_c": values["pretreatment_temp_c"],
    }
    return pd.DataFrame([row])


def vector_from_dict(candidate: dict[str, float], variables: tuple[str, ...]) -> np.ndarray:
    missing = [name for name in variables if name not in candidate]
    if missing:
        raise ValueError(f"candidate is missing {missing}")
    return np.array([float(candidate[name]) for name in variables], dtype=float)


def dict_from_vector(
    vector: np.ndarray | list[float], variables: tuple[str, ...]
) -> dict[str, float]:
    values = np.asarray(vector, dtype=float).ravel()
    if values.size != len(variables):
        raise ValueError(f"expected {len(variables)} values, got {values.size}")
    return {name: float(value) for name, value in zip(variables, values, strict=True)}


# --------------------------------------------------------------------------- constraints
def _constraint_arrays(values: dict[str, float]) -> dict[str, np.ndarray]:
    carb = np.atleast_1d(np.asarray(values["carb_fraction"], dtype=float))
    protein = np.atleast_1d(np.asarray(values["protein_fraction"], dtype=float))
    lipid = 1.0 - carb - protein
    stress = vfa_stress(
        np.atleast_1d(np.asarray(values["olr_kg_vs_m3_d"], dtype=float)), lipid, protein
    )
    solids = np.atleast_1d(np.asarray(values["total_solids_pct"], dtype=float))
    tan = tan_concentration(protein, solids)
    ph_eff = ph_effective(
        np.atleast_1d(np.asarray(values["ph_setpoint"], dtype=float)), stress
    )
    hrt = np.atleast_1d(np.asarray(values["hrt_days"], dtype=float))
    return {"carb": carb, "protein": protein, "lipid": lipid, "stress": stress, "tan": tan,
            "ph_eff": ph_eff, "hrt": hrt}


def _box_violations(values: dict[str, float]) -> list[str]:
    """Names of the declared input ranges that this candidate leaves (SPEC §10 constraint C-b)."""
    arrays = _constraint_arrays(values)
    checks = {
        "carb_fraction": arrays["carb"],
        "protein_fraction": arrays["protein"],
        "lipid_fraction": arrays["lipid"],
        "total_solids_pct": np.atleast_1d(np.asarray(values["total_solids_pct"], dtype=float)),
        "temperature_c": np.atleast_1d(np.asarray(values["temperature_c"], dtype=float)),
        "ph_setpoint": np.atleast_1d(np.asarray(values["ph_setpoint"], dtype=float)),
        "olr_kg_vs_m3_d": np.atleast_1d(np.asarray(values["olr_kg_vs_m3_d"], dtype=float)),
        "hrt_days": arrays["hrt"],
        "inoculum_ratio": np.atleast_1d(np.asarray(values["inoculum_ratio"], dtype=float)),
        "pretreatment_hours": np.atleast_1d(np.asarray(values["pretreatment_hours"], dtype=float)),
        "pretreatment_temp_c": np.atleast_1d(
            np.asarray(values["pretreatment_temp_c"], dtype=float)
        ),
    }
    violated = []
    for name, array in checks.items():
        low, high = config.INPUT_RANGES[name]
        if ((array < low - 1e-9) | (array > high + 1e-9)).any():
            violated.append(name)
    return violated


def constraint_report(candidate: dict[str, float]) -> dict[str, Any]:
    """Every frozen constraint, its value, and whether it holds. Enforced, not just reported."""
    values = full_candidate(candidate)
    arrays = _constraint_arrays(values)
    stress = float(arrays["stress"][0])
    tan = float(arrays["tan"][0])
    ph_eff = float(arrays["ph_eff"][0])
    hrt = float(arrays["hrt"][0])
    box_violations = _box_violations(values)
    limits = config.CONSTRAINTS
    constraints = {
        "C-b": not box_violations,
        "C-c": stress <= limits["stability_max"],
        "C-d": tan <= limits["tan_max_g_per_l"],
        "C-e": limits["ph_min"] <= ph_eff <= limits["ph_max"],
        "C-f": hrt >= limits["hrt_min_days"],
    }
    return {
        "constraints": constraints,
        "violations": [name for name, ok in constraints.items() if not ok],
        "box_violations": box_violations,
        "feasible": all(constraints.values()),
        "stress": stress,
        "tan_g_per_l": tan,
        "ph_eff": ph_eff,
        "hrt_days": hrt,
        "lipid_fraction": float(arrays["lipid"][0]),
    }


def _normalised_violation(values: dict[str, float]) -> np.ndarray:
    """Unitless total violation, 0 for a feasible point. Used by the penalty."""
    arrays = _constraint_arrays(values)
    limits = config.CONSTRAINTS
    total = np.zeros_like(arrays["stress"])
    for name, array in (
        ("carb_fraction", arrays["carb"]),
        ("protein_fraction", arrays["protein"]),
        ("lipid_fraction", arrays["lipid"]),
    ):
        low, high = config.INPUT_RANGES[name]
        width = high - low
        total += np.maximum(0.0, low - array) / width + np.maximum(0.0, array - high) / width
    for name, array in (
        ("total_solids_pct", np.atleast_1d(np.asarray(values["total_solids_pct"], dtype=float))),
        ("temperature_c", np.atleast_1d(np.asarray(values["temperature_c"], dtype=float))),
        ("ph_setpoint", np.atleast_1d(np.asarray(values["ph_setpoint"], dtype=float))),
        ("olr_kg_vs_m3_d", np.atleast_1d(np.asarray(values["olr_kg_vs_m3_d"], dtype=float))),
        ("hrt_days", arrays["hrt"]),
        ("inoculum_ratio", np.atleast_1d(np.asarray(values["inoculum_ratio"], dtype=float))),
        ("pretreatment_hours", np.atleast_1d(
            np.asarray(values["pretreatment_hours"], dtype=float)
        )),
        (
            "pretreatment_temp_c",
            np.atleast_1d(np.asarray(values["pretreatment_temp_c"], dtype=float)),
        ),
    ):
        low, high = config.INPUT_RANGES[name]
        width = high - low
        total += np.maximum(0.0, low - array) / width + np.maximum(0.0, array - high) / width
    total += np.maximum(0.0, arrays["stress"] - limits["stability_max"]) / limits["stability_max"]
    total += np.maximum(0.0, arrays["tan"] - limits["tan_max_g_per_l"]) / limits["tan_max_g_per_l"]
    total += np.maximum(0.0, limits["ph_min"] - arrays["ph_eff"]) / 1.0
    total += np.maximum(0.0, arrays["ph_eff"] - limits["ph_max"]) / 1.0
    total += np.maximum(0.0, limits["hrt_min_days"] - arrays["hrt"]) / limits["hrt_min_days"]
    return total


def assert_feasible(candidate: dict[str, float]) -> dict[str, Any]:
    """Raise rather than report: a recommendation that breaks a constraint is not returned."""
    report = constraint_report(candidate)
    if not report["feasible"]:
        detail = ", ".join(report["violations"])
        out_of_range = ", ".join(report["box_violations"])
        box = f" (out-of-range: {out_of_range})" if report["box_violations"] else ""
        raise RuntimeError(
            f"optimiser returned an infeasible recommendation: violated {detail}{box}; "
            f"stress={report['stress']:.3f} TAN={report['tan_g_per_l']:.3f} g/L "
            f"pH_eff={report['ph_eff']:.3f} HRT={report['hrt_days']:.2f} d"
        )
    return report


# --------------------------------------------------------------------------- objectives
def _yield_array(values: dict[str, float]) -> np.ndarray:
    """True simulator yield at the reference latent values, vectorised over candidates."""
    arrays = _constraint_arrays(values)
    return yield_endpoint(
        carb=arrays["carb"],
        protein=arrays["protein"],
        lipid=arrays["lipid"],
        total_solids=np.atleast_1d(np.asarray(values["total_solids_pct"], dtype=float)),
        temperature=np.atleast_1d(np.asarray(values["temperature_c"], dtype=float)),
        ph=np.atleast_1d(np.asarray(values["ph_setpoint"], dtype=float)),
        olr=np.atleast_1d(np.asarray(values["olr_kg_vs_m3_d"], dtype=float)),
        hrt=arrays["hrt"],
        inoculum=np.atleast_1d(np.asarray(values["inoculum_ratio"], dtype=float)),
        pretreatment_hours=np.atleast_1d(np.asarray(values["pretreatment_hours"], dtype=float)),
        pretreatment_response=np.full(
            arrays["carb"].shape, REFERENCE_LATENT["pretreatment_response"]
        ),
        degradable_mass_loss=np.full(
            arrays["carb"].shape, REFERENCE_LATENT["degradable_mass_loss"]
        ),
    )


def true_objective(candidate: dict[str, float]) -> float:
    """The simulator's own endpoint yield at the reference latent values."""
    return float(_yield_array(full_candidate(candidate))[0])


def penalised_objective(candidate: dict[str, float]) -> float:
    """True yield for a feasible point; a strongly negative score otherwise."""
    values = full_candidate(candidate)
    return float(
        _yield_array(values)[0]
        - PENALTY_PER_UNIT_VIOLATION * _normalised_violation(values)[0]
    )


def build_true_objective(variables: tuple[str, ...], fixed: dict[str, float]) -> Callable:
    """Penalised true objective over a tier's variables (used by the oracle arm).

    Takes a candidate dict so it can be composed directly with `penalised_objective`, and is
    wrapped for the solver by `solver_objective`.
    """

    def objective(candidate: dict[str, float]) -> float:
        return penalised_objective({**fixed, **candidate})

    return objective


def build_surrogate_objective(
    model: FittedModel, variables: tuple[str, ...], fixed: dict[str, float]
) -> Callable:
    """Penalised objective on a trained model's prediction (surrogate arm)."""

    def objective(candidate: dict[str, float]) -> float:
        record = full_candidate({**fixed, **candidate})
        frame = pd.DataFrame(
            [
                {
                    **record,
                    "ph_measured": record["ph_setpoint"],
                    "lipid_fraction": 1.0 - record["carb_fraction"] - record["protein_fraction"],
                }
            ]
        )
        features = transform_features(model.preprocessor, make_feature_frame(frame))
        predicted = float(np.asarray(model.estimator.predict(features), dtype=float).ravel()[0])
        return predicted - PENALTY_PER_UNIT_VIOLATION * float(_normalised_violation(record)[0])

    return objective


def solver_objective(
    objective: Callable, variables: tuple[str, ...]
) -> Callable[[np.ndarray], float]:
    """Adapt a candidate-dict objective to the flat vector the solver works with."""

    def wrapped(vector: np.ndarray) -> float:
        return float(objective(dict_from_vector(vector, variables)))

    return wrapped


# --------------------------------------------------------------------------- solver
def maximise_objective(
    objective: Callable,
    bounds: list[tuple[float, float]],
    *,
    seed: int,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    population_size: int = DEFAULT_POPULATION_SIZE,
) -> tuple[list[float], float]:
    """Bounded global maximisation with a documented seed (SciPy differential evolution).

    Returns the best point (as a list, so the result compares by value) and its value. The
    bounds are hard: every point the solver ever sees is inside them by construction.
    """
    if not bounds:
        raise ValueError("at least one bound is required")
    if max_iterations < 1 or population_size < 2:
        raise ValueError(
            f"max_iterations >= 1 and population_size >= 2 are required "
            f"(got {max_iterations}, {population_size})"
        )
    # SciPy's differential_evolution minimises only, so the objective is negated here and the
    # sign is restored below. Written explicitly because a sign slip would look like a result.
    def negated(point: Any) -> Any:
        return -objective(point)

    result = differential_evolution(
        negated,
        bounds,
        seed=seed,
        maxiter=max_iterations,
        popsize=population_size,
        polish=True,
        updating="immediate",
        init="latinhypercube",
    )
    return [float(value) for value in result.x], float(-result.fun)


def random_search_reference(
    variables: tuple[str, ...],
    *,
    seed: int,
    n_draws: int,
    fixed: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Uniform random sampling of the same box, under the same constraints.

    Used as the comparison arm required by SPEC §10: if a global optimiser cannot beat a handful
    of uniform draws, the optimiser (not the model) is what needs fixing.
    """
    if n_draws < 1:
        raise ValueError(f"n_draws must be >= 1 (got {n_draws})")
    rng = np.random.default_rng(seed + 77)
    bounds = decision_bounds(variables)
    base = dict(fixed or {})
    records: list[dict[str, float]] = []
    for _ in range(n_draws):
        draw = {
            name: float(rng.uniform(low, high))
            for name, (low, high) in zip(variables, bounds, strict=True)
        }
        records.append({**base, **draw})

    best: dict[str, Any] | None = None
    n_feasible = 0
    for record in records:
        report = constraint_report(record)
        if not report["feasible"]:
            continue
        n_feasible += 1
        value = true_objective(record)
        if best is None or value > best["true_yield"]:
            best = {"true_yield": value, "candidate": dict_from_vector(
                vector_from_dict(record, variables), variables), "constraints": report}

    if best is None:
        raise RuntimeError(
            f"none of the {n_draws} random draws was feasible; the feasible set needs re-checking"
        )
    return {**best, "n_draws": n_draws, "n_feasible_draws": n_feasible, "seed": seed}


# --------------------------------------------------------------------------- baselines
def _closest_feasible_mixture(
    process: dict[str, float], target: tuple[float, float]
) -> dict[str, Any]:
    """Deterministic projection of a target mixture onto the feasible set at fixed settings."""
    carb_grid = np.arange(
        config.INPUT_RANGES["carb_fraction"][0],
        config.INPUT_RANGES["carb_fraction"][1] + BASELINE_GRID_STEP / 2,
        BASELINE_GRID_STEP,
    )
    protein_grid = np.arange(
        config.INPUT_RANGES["protein_fraction"][0],
        config.INPUT_RANGES["protein_fraction"][1] + BASELINE_GRID_STEP / 2,
        BASELINE_GRID_STEP,
    )
    best: dict[str, Any] | None = None
    n_feasible = 0
    for carb in carb_grid:
        for protein in protein_grid:
            # explicit conditional: `dict.get(key, other[key])` evaluates its default eagerly
            # and raises KeyError even when the key it is looking for is present
            setpoint = (
                process["ph_measured"] if "ph_measured" in process else process["ph_setpoint"]
            )
            candidate = {
                **process,
                "carb_fraction": float(carb),
                "protein_fraction": float(protein),
                "ph_setpoint": float(setpoint),
            }
            report = constraint_report(candidate)
            if not report["feasible"]:
                continue
            n_feasible += 1
            distance = math.dist((float(carb), float(protein)), target)
            if best is None or distance < best["distance"]:
                best = {
                    "distance": distance,
                    "candidate": {
                        "carb_fraction": float(carb),
                        "protein_fraction": float(protein),
                        "lipid_fraction": 1.0 - float(carb) - float(protein),
                    },
                    "true_yield": true_objective(candidate),
                    "constraints": report,
                }
    if best is None:
        raise RuntimeError("no feasible mixture found at the baseline process settings")
    return {**best, "n_feasible_grid_points": n_feasible, "grid_step": BASELINE_GRID_STEP}


def baseline_reference() -> dict[str, Any]:
    """The declared D6 baseline and a feasible companion, both reported.

    The declared equal-thirds mixture at mid-range settings **violates C-c and C-e** on this
    simulator (measured in Phase 3: stress 1.000 > 0.35, pH_eff 6.20 < 6.5). That is a finding
    about the frozen baseline choice, so it is reported rather than repaired: the declared point
    stays exactly as D6 specifies, and a second, pre-declared comparator - the closest feasible
    mixture at the same process settings, found on a deterministic grid - is used for the F5
    comparison and for the oracle sanity check, because "beats an infeasible baseline" is not
    evidence of anything.
    """
    declared_candidate = {
        "carb_fraction": 1.0 / 3.0,
        "protein_fraction": 1.0 / 3.0,
        "ph_setpoint": config.BASELINE_PROCESS["ph_measured"],
        **config.BASELINE_PROCESS,
    }
    projection = _closest_feasible_mixture(
        {**config.BASELINE_PROCESS, "ph_setpoint": config.BASELINE_PROCESS["ph_measured"]},
        (1.0 / 3.0, 1.0 / 3.0),
    )
    return {
        "declared": {
            "label": "declared equal-thirds baseline (decision D6)",
            "candidate": declared_candidate,
            "true_yield": true_objective(declared_candidate),
            "constraints": constraint_report(declared_candidate),
        },
        "feasible": {
            "label": (
                "feasible projection of equal thirds at the same process settings "
                "(closest feasible grid point; pre-declared comparator)"
            ),
            "candidate": projection["candidate"],
            "true_yield": projection["true_yield"],
            "constraints": projection["constraints"],
            "distance_to_equal_thirds": projection["distance"],
            "n_feasible_grid_points": projection["n_feasible_grid_points"],
            "grid_step": projection["grid_step"],
        },
    }


# --------------------------------------------------------------------------- robustness
def perturbation_report(
    candidate: dict[str, float],
    variables: tuple[str, ...],
    *,
    draws: int = DEFAULT_PERTURBATION_DRAWS,
    seed: int,
    fixed: dict[str, float] | None = None,
    fraction: float = config.PERTURBATION_FRACTION,
) -> dict[str, Any]:
    """± `fraction` of each variable's range width, re-evaluated on the true simulator.

    The evaluation set is the recommendation itself (draw 0, the exact centre) plus `draws - 1`
    random perturbations inside the ±fraction ball, each clipped into its declared bound. Shifts
    that had to be clipped are counted and reported; a perturbation can still leave the *derived*
    lipid fraction outside its band, and those draws are counted as constraint violations rather
    than repaired, because that is exactly the knife-edge behaviour F5 is looking for.
    """
    if draws < 1:
        raise ValueError(f"draws must be >= 1 (got {draws})")
    if not 0.0 < fraction < 1.0:
        raise ValueError(f"fraction must be in (0, 1) (got {fraction})")

    bounds = decision_bounds(variables)
    base = dict(fixed or {})
    rng = np.random.default_rng(seed + 991)
    centre = vector_from_dict(candidate, variables)
    widths = np.array([high - low for low, high in bounds], dtype=float)
    shifts = rng.uniform(-fraction, fraction, size=(draws - 1, len(variables))) * widths
    raw = np.vstack([np.zeros((1, len(variables))), shifts])
    shifted = centre + raw
    low = np.array([bound[0] for bound in bounds], dtype=float)
    high = np.array([bound[1] for bound in bounds], dtype=float)
    clipped = np.clip(shifted, low, high)
    n_clipped = int(np.any(np.abs(clipped - shifted) > 1e-12, axis=1).sum())

    yields: list[float] = []
    n_feasible = 0
    best_edge = 0.0
    best_yield = -math.inf
    min_by_variable = {name: math.inf for name in variables}
    max_by_variable = {name: -math.inf for name in variables}
    for index in range(draws):
        point = dict_from_vector(clipped[index], variables)
        values = {**base, **point}
        report = constraint_report(values)
        for name, value in point.items():
            min_by_variable[name] = min(min_by_variable[name], value)
            max_by_variable[name] = max(max_by_variable[name], value)
        if not report["feasible"]:
            continue
        n_feasible += 1
        value = true_objective(values)
        yields.append(value)
        if value > best_yield:
            best_yield = value
            edge = 0.0
            for position in range(len(variables)):
                radius = fraction * widths[position]
                edge = max(edge, abs(raw[index, position]) / radius)
            best_edge = min(edge, 1.0)

    centre_yield = true_objective({**base, **candidate})
    # A candidate that is itself infeasible (or one whose whole ball is infeasible) has no yield
    # statistics to report. That is a result, not an error: the fields are None and the caller
    # must say so rather than receive a fabricated number.
    stats = (
        {
            "mean_yield": float(np.mean(yields)),
            "min_yield": float(np.min(yields)),
            "max_yield": float(np.max(yields)),
        }
        if yields
        else {"mean_yield": None, "min_yield": None, "max_yield": None}
    )
    return {
        "draws": draws,
        "fraction": fraction,
        "seed": seed,
        "variables": list(variables),
        "centre_yield": centre_yield,
        **stats,
        "n_feasible": n_feasible,
        "n_infeasible": draws - n_feasible,
        "feasible_fraction": n_feasible / draws,
        "n_clipped": n_clipped,
        "best_edge_fraction": best_edge,
        "min_by_variable": min_by_variable,
        "max_by_variable": max_by_variable,
        "note": (
            "draw 0 is the recommendation itself; the other draws are uniform inside the "
            "+/-fraction ball and clipped into the declared bounds (n_clipped reports how many "
            "draws had to be clipped)"
        ),
    }


def evaluate_f5(
    perturbation: dict[str, Any], *, feasible_reference_yield: float, declared_baseline_yield: float
) -> dict[str, Any]:
    """Rule F5 (SPEC §9.1): is the recommendation robust to ±5 %, or is it an artefact?

    Three conditions, all pre-declared here and all reported:
      * `below_reference` - the mean perturbed yield falls below the feasible reference baseline;
      * `knife_edge` - more than half the perturbed draws violate a constraint, i.e. the
        recommendation sits on the edge of the feasible set rather than inside it;
      * `not_stationary` - the best perturbed draw sits at the edge of the ±fraction ball, so
        small changes move the best point outward instead of back to the recommendation.
    """
    mean_yield = perturbation["mean_yield"]
    conditions = {
        # None means "not evaluable": no perturbed draw was feasible at all
        "below_reference": (
            None if mean_yield is None else bool(mean_yield < feasible_reference_yield)
        ),
        "knife_edge": bool(perturbation["feasible_fraction"] < F5_KNIFE_EDGE_THRESHOLD),
        "not_stationary": bool(perturbation["best_edge_fraction"] >= F5_EDGE_THRESHOLD),
    }
    fires = any(value for value in conditions.values() if value is not None)
    return {
        "f5_rule": (
            "fires if any of: mean perturbed yield below the feasible reference baseline "
            f"({feasible_reference_yield:.2f}); feasible fraction of perturbed draws below "
            f"{F5_KNIFE_EDGE_THRESHOLD}; best perturbed draw at or beyond "
            f"{F5_EDGE_THRESHOLD} of the +/-{config.PERTURBATION_FRACTION:.0%} ball edge"
        ),
        "f5_fires": fires,
        "f5_conditions": conditions,
        "f5_verdict": (
            "artefactual - report the recommendation as fragile, do not call it a best recipe"
            if fires
            else "robust enough to report, with the perturbation numbers alongside"
        ),
        "f5_knife_edge_threshold": F5_KNIFE_EDGE_THRESHOLD,
        "f5_edge_threshold": F5_EDGE_THRESHOLD,
        "feasible_reference_yield": float(feasible_reference_yield),
        "declared_baseline_yield": float(declared_baseline_yield),
        "mean_perturbed_yield": None if mean_yield is None else float(mean_yield),
        "feasible_fraction": float(perturbation["feasible_fraction"]),
        "best_edge_fraction": float(perturbation["best_edge_fraction"]),
    }


# --------------------------------------------------------------------------- the three arms
def _check_models(model_names: tuple[str, ...]) -> None:
    unknown = [name for name in model_names if name not in config.MODEL_NAMES]
    if unknown:
        raise ValueError(
            f"unknown model(s) {unknown}; the five declared models are {config.MODEL_NAMES}"
        )
    if not model_names:
        raise ValueError("at least one model is required for the surrogate arm")


def _check_tiers(tiers: tuple[str, ...]) -> None:
    unknown = [name for name in tiers if name not in TIER_NAMES]
    if unknown:
        raise ValueError(f"unknown tier(s) {unknown}; the two frozen runs are {TIER_NAMES}")


def _tier_variables(tier: str) -> tuple[str, ...]:
    return C1_VARIABLES if tier == "C1" else LAB_VARIABLES


def _tier_held_fixed(tier: str) -> dict[str, dict[str, Any]]:
    held = dict(HELD_FIXED)
    if tier == "C1":
        held.update(C1_HELD_FIXED)
    return held


def _fixed_values(held: dict[str, dict[str, Any]]) -> dict[str, float]:
    return {name: float(entry["value"]) for name, entry in held.items()}


def _tier_label(tier: str) -> str:
    return (
        "achievable at home (tier C1)"
        if tier == "C1"
        else "laboratory recommendation (tiers C1 + C2)"
    )


def run_optimisation(
    *,
    seed: int,
    n_scenarios: int,
    model_names: tuple[str, ...],
    tiers: tuple[str, ...] = TIER_NAMES,
    perturbation_draws: int = DEFAULT_PERTURBATION_DRAWS,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    population_size: int = DEFAULT_POPULATION_SIZE,
    random_search_draws: int | None = None,
) -> dict[str, Any]:
    """Run all three arms for each requested tier, with robustness, on one seed."""
    _check_models(model_names)
    _check_tiers(tiers)
    if n_scenarios < MIN_SCENARIOS:
        raise ValueError(
            f"at least {MIN_SCENARIOS} scenarios are required for a grouped 70/15/15 split "
            f"(got {n_scenarios})"
        )
    # Equal evaluation budget for the comparison arm, pre-declared rather than tuned.
    draws = (
        random_search_draws
        if random_search_draws is not None
        else max_iterations * population_size
    )

    frame, _ = simulate(seed=seed, n_scenarios=n_scenarios)
    splits = split_frame(frame)
    fitted = fit_all_models(splits, seed, names=model_names)
    reference = baseline_reference()
    declared_yield = reference["declared"]["true_yield"]
    feasible_yield = reference["feasible"]["true_yield"]

    tier_results: dict[str, Any] = {}
    for tier in tiers:
        variables = _tier_variables(tier)
        held = _tier_held_fixed(tier)
        fixed = _fixed_values(held)
        bounds = decision_bounds(variables)

        true_objective_fn = build_true_objective(variables, fixed)
        best_point, best_value = maximise_objective(
            solver_objective(true_objective_fn, variables),
            bounds,
            seed=seed,
            max_iterations=max_iterations,
            population_size=population_size,
        )
        true_candidate = dict_from_vector(best_point, variables)
        true_report = assert_feasible({**fixed, **true_candidate})

        random_arm = random_search_reference(
            variables, seed=seed, n_draws=draws, fixed=fixed
        )

        arms: dict[str, Any] = {
            "true": {
                "label": "oracle arm: optimises the simulator itself (impossible in reality)",
                "candidate": true_candidate,
                "true_yield": float(best_value),
                "constraints": true_report,
            },
            "random_search": {
                "label": "equal-budget uniform random search on the true simulator",
                "candidate": random_arm["candidate"],
                "true_yield": random_arm["true_yield"],
                "constraints": random_arm["constraints"],
                "n_draws": random_arm["n_draws"],
                "n_feasible_draws": random_arm["n_feasible_draws"],
            },
            "baseline": {
                "label": reference["declared"]["label"],
                "candidate": reference["declared"]["candidate"],
                "true_yield": declared_yield,
                "constraints": reference["declared"]["constraints"],
            },
            "surrogate": {},
        }

        for name, model in fitted.items():
            surrogate_objective_fn = build_surrogate_objective(model, variables, fixed)
            point, predicted = maximise_objective(
                solver_objective(surrogate_objective_fn, variables),
                bounds,
                seed=seed,
                max_iterations=max_iterations,
                population_size=population_size,
            )
            candidate = dict_from_vector(point, variables)
            report = assert_feasible({**fixed, **candidate})
            arm_true_yield = true_objective({**fixed, **candidate})
            arms["surrogate"][name] = {
                "label": (
                    f"surrogate arm: optimises {name}'s prediction, "
                    "re-scored on the simulator"
                ),
                "candidate": candidate,
                "predicted_yield": float(predicted),
                "true_yield": arm_true_yield,
                "gap": float(predicted) - arm_true_yield,
                "constraints": report,
            }

        perturbation = perturbation_report(
            true_candidate, variables, draws=perturbation_draws, seed=seed, fixed=fixed
        )
        for arm in [arms["true"], arms["random_search"], *arms["surrogate"].values()]:
            arm_perturbation = perturbation_report(
                arm["candidate"], variables, draws=perturbation_draws, seed=seed, fixed=fixed
            )
            arm["perturbation"] = arm_perturbation
            arm["f5"] = evaluate_f5(
                arm_perturbation,
                feasible_reference_yield=feasible_yield,
                declared_baseline_yield=declared_yield,
            )

        tier_results[tier] = {
            "tier_label": _tier_label(tier),
            "variables": list(variables),
            "held_fixed": held,
            "bounds": {name: list(bound) for name, bound in zip(variables, bounds, strict=True)},
            "objective": "penalised simulated_methane_yield_ml_per_g_vs (constraints enforced)",
            "solver": {
                "method": (
                    "scipy.optimize.differential_evolution "
                    "(polish=True, latin hypercube start)"
                ),
                "seed": seed,
                "max_iterations": max_iterations,
                "population_size": population_size,
                "random_search_draws": draws,
                "equal_budget": True,
            },
            "arms": arms,
            "perturbation": perturbation,
            "f5": evaluate_f5(
                perturbation,
                feasible_reference_yield=feasible_yield,
                declared_baseline_yield=declared_yield,
            ),
            "checks": {
                "feasible_reference_yield": feasible_yield,
                "declared_baseline_yield": declared_yield,
                "random_search_yield": random_arm["true_yield"],
                "oracle_beats_reference": bool(best_value >= feasible_yield - 1e-6),
            },
        }

    return {
        "seed": seed,
        "n_scenarios": n_scenarios,
        "model_names": list(model_names),
        "tiers": tier_results,
        "baseline": reference,
        "caveat": CAVEAT,
        "scope_note": SCOPE_NOTE,
        "reference_latent": dict(REFERENCE_LATENT),
        "simulated": True,
    }


# --------------------------------------------------------------------------- artefacts
def _write_csv(frame: pd.DataFrame, path: Path) -> Path:
    frame = frame.copy()
    frame["simulated"] = config.SIMULATED_MARKER
    frame["simulator_version"] = config.SIMULATOR_VERSION
    frame.to_csv(path, index=False)
    return path


def _recommendation_row(
    tier: str, arm: str, model: str | None, payload: dict[str, Any]
) -> dict[str, Any]:
    values = full_candidate(payload["candidate"])
    row = {
        "tier": tier,
        "arm": arm,
        "model": model or "-",
        "true_yield": payload["true_yield"],
        "predicted_yield": payload.get("predicted_yield", ""),
        "gap": payload.get("gap", ""),
        "f5_fires": payload["f5"]["f5_fires"] if "f5" in payload else False,
    }
    for column in config.FEATURES:
        row[column] = float(values.get(column, np.nan))
    row["lipid_fraction"] = float(1.0 - values["carb_fraction"] - values["protein_fraction"])
    row["ph_measured"] = float(values["ph_setpoint"])
    return row


def write_optimiser_results(result: dict[str, Any], outdir: Path | str) -> dict[str, Path]:
    """Write the three arms for both tiers, the summary table and the metadata."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    recommendation_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for tier, payload in result["tiers"].items():
        for arm_name in ("true", "random_search", "baseline"):
            arm = payload["arms"][arm_name]
            recommendation_rows.append(_recommendation_row(tier, arm_name, None, arm))
        for model_name, arm in payload["arms"]["surrogate"].items():
            recommendation_rows.append(_recommendation_row(tier, "surrogate", model_name, arm))
        for arm_name, arm in (
            ("oracle", payload["arms"]["true"]),
            ("random_search", payload["arms"]["random_search"]),
            ("baseline", payload["arms"]["baseline"]),
        ):
            summary_rows.append(
                {
                    "tier": tier,
                    "tier_label": payload["tier_label"],
                    "arm": arm_name,
                    "model": "-",
                    "true_yield": arm["true_yield"],
                    "predicted_yield": arm.get("predicted_yield", ""),
                    "gap": arm.get("gap", ""),
                    "f5_fires": arm.get("f5", {}).get("f5_fires", False),
                    "feasible": arm["constraints"]["feasible"],
                    "oracle_beats_reference": payload["checks"]["oracle_beats_reference"],
                }
            )
        for model_name, arm in payload["arms"]["surrogate"].items():
            summary_rows.append(
                {
                    "tier": tier,
                    "tier_label": payload["tier_label"],
                    "arm": "surrogate",
                    "model": model_name,
                    "true_yield": arm["true_yield"],
                    "predicted_yield": arm["predicted_yield"],
                    "gap": arm["gap"],
                    "f5_fires": arm["f5"]["f5_fires"],
                    "feasible": arm["constraints"]["feasible"],
                    "oracle_beats_reference": payload["checks"]["oracle_beats_reference"],
                }
            )

    metadata = {
        "simulated": True,
        "data_provenance": config.DATA_PROVENANCE,
        "simulator_version": config.SIMULATOR_VERSION,
        "as_of": config.AS_OF,
        "seed": result["seed"],
        "n_scenarios": result["n_scenarios"],
        "models": result["model_names"],
        "tiers": list(result["tiers"]),
        "reference_latent": result["reference_latent"],
        "penalty_per_unit_violation": PENALTY_PER_UNIT_VIOLATION,
        "caveat": result["caveat"],
        "scope_note": result["scope_note"],
        "baseline_declared": {
            "label": result["baseline"]["declared"]["label"],
            "true_yield": result["baseline"]["declared"]["true_yield"],
            "feasible": result["baseline"]["declared"]["constraints"]["feasible"],
            "violations": result["baseline"]["declared"]["constraints"]["violations"],
        },
        "baseline_feasible_reference": {
            "label": result["baseline"]["feasible"]["label"],
            "true_yield": result["baseline"]["feasible"]["true_yield"],
            "feasible": result["baseline"]["feasible"]["constraints"]["feasible"],
            "distance_to_equal_thirds": result["baseline"]["feasible"]["distance_to_equal_thirds"],
        },
        "package_versions": {
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
        },
    }

    return {
        "recommendations": _write_csv(
            pd.DataFrame(recommendation_rows), outdir / "optimiser_recommendations.csv"
        ),
        "summary": _write_csv(pd.DataFrame(summary_rows), outdir / "optimiser_summary.csv"),
        "metadata": _write_json(metadata, outdir / "optimiser_metadata.json"),
    }


def _write_json(payload: dict[str, Any], path: Path) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------- CLI
def _parse_models(text: str) -> tuple[str, ...]:
    names = tuple(part.strip() for part in text.split(",") if part.strip())
    if not names:
        raise ValueError("at least one model is required (--models)")
    _check_models(names)
    return names


def _parse_tiers(text: str) -> tuple[str, ...]:
    names = tuple(part.strip() for part in text.split(",") if part.strip())
    if not names:
        raise ValueError("at least one tier is required (--tiers)")
    _check_tiers(names)
    return names


def _parse_seed(text: str) -> int:
    try:
        return int(text)
    except ValueError as exc:
        raise ValueError(f"could not read the seed {text!r}: {exc}") from exc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Constrained, uncertainty-aware optimisation over the SIMULATED surface (SPEC_V1 10)."
        )
    )
    parser.add_argument("--seed", default=str(config.SEEDS[0]))
    parser.add_argument("--n-scenarios", type=int, default=config.N_SCENARIOS)
    parser.add_argument("--models", default=",".join(config.MODEL_NAMES))
    parser.add_argument("--tiers", default=",".join(TIER_NAMES))
    parser.add_argument("--perturbation-draws", type=int, default=DEFAULT_PERTURBATION_DRAWS)
    parser.add_argument("--max-iterations", type=int, default=DEFAULT_MAX_ITERATIONS)
    parser.add_argument("--population-size", type=int, default=DEFAULT_POPULATION_SIZE)
    parser.add_argument("--outdir", default=str(config.RESULTS_DIR))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    seed = _parse_seed(args.seed)
    models = _parse_models(args.models)
    tiers = _parse_tiers(args.tiers)

    result = run_optimisation(
        seed=seed,
        n_scenarios=args.n_scenarios,
        model_names=models,
        tiers=tiers,
        perturbation_draws=args.perturbation_draws,
        max_iterations=args.max_iterations,
        population_size=args.population_size,
    )
    paths = write_optimiser_results(result, args.outdir)

    for tier, payload in result["tiers"].items():
        print(f"tier {tier} - {payload['tier_label']} [SIMULATED]")
        for arm_name, arm in (
            ("oracle", payload["arms"]["true"]),
            ("random_search", payload["arms"]["random_search"]),
            ("baseline (declared D6)", payload["arms"]["baseline"]),
        ):
            print(
                f"  {arm_name}: true yield {arm['true_yield']:.2f} "
                f"(feasible={arm['constraints']['feasible']}) [SIMULATED]"
            )
        for model_name, arm in payload["arms"]["surrogate"].items():
            print(
                f"  surrogate {model_name}: predicted {arm['predicted_yield']:.2f} -> true "
                f"{arm['true_yield']:.2f} (gap {arm['gap']:+.2f}) [SIMULATED]"
            )
        print(
            f"  perturbation +/-{config.PERTURBATION_FRACTION:.0%}: mean "
            f"{payload['perturbation']['mean_yield']:.2f}, feasible "
            f"{payload['perturbation']['feasible_fraction']:.0%} of draws; "
            f"F5: {payload['f5']['f5_verdict']} [SIMULATED]"
        )
    print(f"warning: {CAVEAT}")
    print(f"wrote {len(paths)} artefacts to {Path(args.outdir)} [SIMULATED]")
    return 0


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
