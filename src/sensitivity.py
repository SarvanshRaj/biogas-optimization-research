"""The pre-declared sensitivity sweep (SPEC_V1 §11) - SIMULATED data only.

The specification fixes **exactly ten** assumptions, three levels each, and says nothing else may
be swept "so that the sensitivity analysis cannot be chosen after seeing results". This module is
the machinery for that promise: the ten assumptions and their levels are declared here, quoted from
the specification, and a test compares them to the numbers written in the specification file.

Mechanism. Most levels are a *constant* change, which is applied by temporarily patching the
module attributes in `src.config` inside a context manager that restores them even if the body
raises. One level is *structural* - the total-solids response shape - and is implemented as a
declared second form in `src.simulate_data.f_load` (see `config.TS_SHAPE`). The nominal level of
every assumption exists in the grid so that each delta is measured against a run of the *same*
configuration, never against a literature value the code never executed.

What a sweep row means, and what it does not. Each row re-runs the whole chain - generate, fit,
optimise - under one changed assumption, and reports the median simulated yield and the optimiser's
recommendation for both tiers. It describes **the simulator's** sensitivity. It says nothing about
how a real digester would respond to a different biodegradability or a different pre-treatment
response distribution, and the sweep scale (declared in the metadata, smaller than the study
configuration) is recorded with every row for exactly that reason.
"""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pandas as pd

from src import config
from src.optimize import TIER_NAMES, run_optimisation
from src.simulate_data import simulate

# --------------------------------------------------------------------------- override mechanism
#: The constants a sweep level may move. Anything else is refused, so a typo cannot silently
#: patch an unrelated part of the configuration.
OVERRIDABLE_CONSTANTS: tuple[str, ...] = (
    "BETA",
    "ETA_LCFA",
    "C_LCFA_HALF",
    "C_TAN_HALF",
    "K_REF",
    "T_MESO_SIGMA",
    "TS_CENTRE",
    "TS_SHAPE",
    "RESPONSE_CENTRE",
    "NOISE_SCALE",
    "SIGMA_SCENARIO",
    "SIGMA_REPLICATE",
    "MISSING_RATE_PH",
    "MISSING_RATE_TEMP",
)

#: The frozen values, captured at import time and never reassigned.
_FROZEN_VALUES: dict[str, Any] = {name: getattr(config, name) for name in OVERRIDABLE_CONSTANTS}


def frozen_values() -> dict[str, Any]:
    """The frozen value of every overridable constant."""
    return dict(_FROZEN_VALUES)


@contextmanager
def constant_override(**patches: Any) -> Iterator[None]:
    """Temporarily patch `src.config` constants; always restore, even on failure.

    This is deliberate global mutable state. It is safe here because the sweep is single-threaded,
    the restore is in a `finally`, and a test proves that a raise inside the body leaves the
    constants untouched and that every nominal level reproduces the committed dataset.
    """
    unknown = sorted(set(patches) - set(OVERRIDABLE_CONSTANTS))
    if unknown:
        raise ValueError(
            f"{unknown} is not an overridable constant; the sweep may only move "
            f"{list(OVERRIDABLE_CONSTANTS)}"
        )
    previous = {name: getattr(config, name) for name in patches}
    try:
        for name, value in patches.items():
            setattr(config, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(config, name, value)


# --------------------------------------------------------------------------- the declared grid
def _level(
    label: str, value: float, *, is_nominal: bool | None = None, **patches: Any
) -> dict[str, Any]:
    """One constant level: `label` is what the specification prints, `value` is the number.

    `is_nominal` is normally derived: a level is nominal when every patch equals the frozen value.
    It is stated explicitly for the one assumption where the specification's wording and the frozen
    configuration disagree (see the missingness entry).
    """
    entry: dict[str, Any] = {"level": label, "value": value, "kind": "constant", "patches": patches}
    derived = all(_FROZEN_VALUES.get(name) == value for name, value in patches.items())
    entry["is_nominal"] = derived if is_nominal is None else is_nominal
    return entry


def _structural(label: str, description: str, **patches: Any) -> dict[str, Any]:
    return {"level": label, "value": None, "kind": "structural", "patches": patches,
            "label": description, "is_nominal": False}


SENSITIVITY_ASSUMPTIONS: dict[str, dict[str, Any]] = {
    "beta": {
        "label": "beta (biodegradability)",
        "source": "SPEC_V1 11 row 1",
        "note": "multiplies the degradable fraction; a purely multiplicative ceiling change",
        "levels": [
            _level(
                "0.85",
                float("0.85"), BETA=0.85),
            _level(
                "0.95",
                float("0.95"), BETA=0.95),
            _level(
                "1.00",
                float("1.00"), BETA=1.00),
        ],
    },
    "eta_lcfa": {
        "label": "eta (LCFA partition)",
        "source": "SPEC_V1 11 row 2",
        "note": "fraction of lipid appearing as inhibitory LCFA",
        "levels": [
            _level(
                "0.005",
                float("0.005"), ETA_LCFA=0.005),
            _level(
                "0.012",
                float("0.012"), ETA_LCFA=0.012),
            _level(
                "0.030",
                float("0.030"), ETA_LCFA=0.030),
        ],
    },
    "lcfa_half": {
        "label": "LCFA half-saturation",
        "source": "SPEC_V1 11 row 3",
        "note": "concentration at which the LCFA penalty halves; never resolved by the sources",
        "levels": [
            _level(
                "0.8",
                float("0.8"), C_LCFA_HALF=0.8),
            _level(
                "1.2",
                float("1.2"), C_LCFA_HALF=1.2),
            _level(
                "2.0",
                float("2.0"), C_LCFA_HALF=2.0),
        ],
    },
    "tan_half": {
        "label": "TAN half-saturation",
        "source": "SPEC_V1 11 row 4",
        "note": "the ammonia threshold spread is carried rather than resolved",
        "levels": [
            _level(
                "4.0",
                float("4.0"), C_TAN_HALF=4.0),
            _level(
                "6.0",
                float("6.0"), C_TAN_HALF=6.0),
            _level(
                "10.0",
                float("10.0"), C_TAN_HALF=10.0),
        ],
    },
    "k_ref": {
        "label": "k_ref",
        "source": "SPEC_V1 11 row 5",
        "note": "first-order rate constant; changes how much of the ceiling the window completes",
        "levels": [
            _level(
                "0.10",
                float("0.10"), K_REF=0.10),
            _level(
                "0.18",
                float("0.18"), K_REF=0.18),
            _level(
                "0.25",
                float("0.25"), K_REF=0.25),
        ],
    },
    "sigma_t_meso": {
        "label": "sigma_T mesophilic",
        "source": "SPEC_V1 11 row 6",
        "note": "width of the mesophilic temperature optimum",
        "levels": [
            _level(
                "7.0",
                float("7.0"), T_MESO_SIGMA=7.0),
            _level(
                "10.0",
                float("10.0"), T_MESO_SIGMA=10.0),
            _level(
                "14.0",
                float("14.0"), T_MESO_SIGMA=14.0),
        ],
    },
    "ts_shape": {
        "label": "TS shape",
        "source": "SPEC_V1 11 row 7",
        "note": "the total-solids direction is contested (claim C-005); this is where it is probed",
        "levels": [
            _level(
                "12.0",
                float("12.0"), TS_SHAPE="peak", TS_CENTRE=12.0),
            _structural(
                "monotone",
                "monotone increasing (CIT-0006's direction)",
                TS_SHAPE="monotone",
            ),
            _level(
                "20.0",
                float("20.0"), TS_SHAPE="peak", TS_CENTRE=20.0),
        ],
    },
    "pretreatment_response": {
        "label": "pre-treatment response distribution",
        "source": "SPEC_V1 11 row 8",
        "note": (
            "the whole point of Q2: the response distribution is swept, never assumed "
            "beneficial"
        ),
        "levels": [
            _level(
                "0.90",
                float("0.90"),
                RESPONSE_CENTRE=0.90,
            ),
            _level(
                "1.00",
                float("1.00"), RESPONSE_CENTRE=1.00),
            _level(
                "1.10",
                float("1.10"), RESPONSE_CENTRE=1.10),
        ],
    },
    "noise_scale": {
        "label": "noise scale",
        "source": "SPEC_V1 11 row 9",
        "note": "both sigmas scaled together",
        "levels": [
            _level(
                "0.5",
                float("0.5"), NOISE_SCALE=0.5),
            _level(
                "1.0",
                float("1.0"), NOISE_SCALE=1.0),
            _level(
                "2.0",
                float("2.0"), NOISE_SCALE=2.0),
        ],
    },
    "missingness": {
        "label": "missingness rate",
        "source": "SPEC_V1 11 row 10",
        "note": (
            "the specification prints a single rate, while the frozen simulator carries two "
            "(2 % for pH and 1.5 % for temperature). The nominal level therefore keeps the "
            "simulator's pair, so that a delta of exactly zero is measurable, and the 0 % / 5 % "
            "levels set both rates. This wording gap is recorded rather than resolved silently"
        ),
        "levels": [
            _level(
                "0.0",
                float("0.0"), MISSING_RATE_PH=0.0, MISSING_RATE_TEMP=0.0),
            _level(
                "0.02",
                float("0.02"),
                is_nominal=True,  # the frozen pair, not 2 % for both: see the note
                MISSING_RATE_PH=0.02, MISSING_RATE_TEMP=0.015),
            _level(
                "0.05",
                float("0.05"), MISSING_RATE_PH=0.05, MISSING_RATE_TEMP=0.05),
        ],
    },
}

SWEEP_SCALE_NOTE = (
    "Each sweep row re-runs generate -> fit -> optimise under one changed assumption at the "
    "sweep configuration recorded in this metadata. That configuration is a runtime choice and is "
    "not the study configuration: the sweep measures the sign and rough size of each effect, not "
    "its precise value at study size."
)
NOTHING_ELSE_SWEPT = (
    "Exactly the ten assumptions of SPEC_V1 11 were swept, three pre-declared levels each. No "
    "other constant, structural choice or analysis option was varied, which is what makes the "
    "sweep reproducible rather than exploratory."
)
CAVEAT = (
    "These numbers describe how sensitive the SIMULATOR is to its own assumptions. They are not "
    "measurements, they do not transfer to real food waste or real digesters, and a small "
    "sensitivity here means the assumption matters little *in this model*, not that it is "
    "unimportant in reality."
)


def _resolve(assumption: str, level: str) -> dict[str, Any]:
    if assumption not in SENSITIVITY_ASSUMPTIONS:
        raise ValueError(
            f"unknown assumption {assumption!r}; the sweep covers exactly "
            f"{sorted(SENSITIVITY_ASSUMPTIONS)}"
        )
    for entry in SENSITIVITY_ASSUMPTIONS[assumption]["levels"]:
        if entry["level"] == str(level):
            return entry
    declared = [str(entry["level"]) for entry in SENSITIVITY_ASSUMPTIONS[assumption]["levels"]]
    raise ValueError(f"unknown level {level!r} for {assumption!r}; declared levels are {declared}")


def sweep_level(
    assumption: str,
    level: str,
    *,
    seed: int,
    n_scenarios: int,
    model_names: tuple[str, ...],
    max_iterations: int = 20,
    population_size: int = 8,
    perturbation_draws: int = 20,
) -> dict[str, Any]:
    """Re-run the chain under one assumption level and report yield plus recommendations."""
    entry = _resolve(assumption, level)
    with constant_override(**entry["patches"]):
        frame, _ = simulate(seed=seed, n_scenarios=n_scenarios)
        median_yield = float(frame[config.TARGET].median())
        result = run_optimisation(
            seed=seed,
            n_scenarios=n_scenarios,
            model_names=model_names,
            perturbation_draws=perturbation_draws,
            max_iterations=max_iterations,
            population_size=population_size,
        )
    tiers = result["tiers"]
    row: dict[str, Any] = {
        "assumption": assumption,
        "label": SENSITIVITY_ASSUMPTIONS[assumption]["label"],
        "level": str(level),
        "kind": entry["kind"],
        "is_nominal": entry["is_nominal"],
        "patches": entry["patches"],
        "median_yield": median_yield,
        "median_yield_std_over_scenarios": float(
            frame.groupby("scenario_id")[config.TARGET].median().std()
        ),
    }
    for tier in TIER_NAMES:
        key = tier.lower().replace("+", "_")
        payload = tiers[tier]
        row[f"{key}_yield"] = float(payload["arms"]["true"]["true_yield"])
        row[f"{key}_feasible"] = bool(payload["arms"]["true"]["constraints"]["feasible"])
        row[f"{key}_f5_fires"] = bool(payload["f5"]["f5_fires"])
    return row


def run_sensitivity_sweep(
    *,
    seed: int,
    n_scenarios: int,
    model_names: tuple[str, ...],
    assumptions: tuple[str, ...] | None = None,
    max_iterations: int = 20,
    population_size: int = 8,
    perturbation_draws: int = 20,
) -> dict[str, Any]:
    """All three levels of every requested assumption, with deltas against its nominal level."""
    chosen = tuple(SENSITIVITY_ASSUMPTIONS if assumptions is None else assumptions)
    if not chosen:
        raise ValueError("at least one assumption is required")
    unknown = [name for name in chosen if name not in SENSITIVITY_ASSUMPTIONS]
    if unknown:
        raise ValueError(
            f"unknown assumption(s) {unknown}; the sweep covers exactly "
            f"{sorted(SENSITIVITY_ASSUMPTIONS)}"
        )

    started = time.time()
    rows: list[dict[str, Any]] = []
    for assumption in chosen:
        for entry in SENSITIVITY_ASSUMPTIONS[assumption]["levels"]:
            rows.append(
                sweep_level(
                    assumption,
                    str(entry["level"]),
                    seed=seed,
                    n_scenarios=n_scenarios,
                    model_names=model_names,
                    max_iterations=max_iterations,
                    population_size=population_size,
                    perturbation_draws=perturbation_draws,
                )
            )

    frame = pd.DataFrame(rows)
    for slug, group in frame.groupby("assumption", sort=False):
        nominal = group[group["is_nominal"]]
        if nominal.empty:
            raise RuntimeError(
                f"assumption {slug!r} has no nominal level, so no like-for-like delta exists"
            )
        for column in ("median_yield", "c1_yield", "c1_c2_yield"):
            reference = float(nominal[column].iloc[0])
            frame.loc[group.index, f"{column}_delta_pct"] = (
                100.0 * (group[column] - reference) / reference
            )
    # pandas types the record keys as Hashable; they are column names here, so the conversion
    # is explicit instead of a cast
    row_records: list[dict[str, Any]] = [
        {str(key): value for key, value in record.items()}
        for record in frame.to_dict(orient="records")
    ]

    metadata = {
        "simulated": True,
        "data_provenance": config.DATA_PROVENANCE,
        "simulator_version": config.SIMULATOR_VERSION,
        "as_of": config.AS_OF,
        "seed": seed,
        "n_scenarios": n_scenarios,
        "model_names": list(model_names),
        "assumptions": list(chosen),
        "assumption_notes": {
            name: {"label": SENSITIVITY_ASSUMPTIONS[name]["label"],
                   "source": SENSITIVITY_ASSUMPTIONS[name]["source"],
                   "note": SENSITIVITY_ASSUMPTIONS[name]["note"]}
            for name in chosen
        },
        "n_rows": len(row_records),
        "solver": {
            "max_iterations": max_iterations,
            "population_size": population_size,
            "perturbation_draws": perturbation_draws,
        },
        "runtime_s": round(time.time() - started, 1),
        "sweep_scale_note": SWEEP_SCALE_NOTE,
        "nothing_else_swept": NOTHING_ELSE_SWEPT,
        "caveat": CAVEAT,
        "frozen_values": {name: value for name, value in frozen_values().items()},
    }
    return {"rows": row_records, "metadata": metadata}


# --------------------------------------------------------------------------- artefacts
def write_sweep_results(result: dict[str, Any], outdir: Path | str) -> dict[str, Path]:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(result["rows"]).copy()
    frame["simulated"] = config.SIMULATED_MARKER
    frame["simulator_version"] = config.SIMULATOR_VERSION
    sweep_path = outdir / "sensitivity_sweep.csv"
    frame.to_csv(sweep_path, index=False)
    metadata_path = outdir / "sensitivity_metadata.json"
    metadata_path.write_text(
        json.dumps(result["metadata"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {"sweep": sweep_path, "metadata": metadata_path}


# --------------------------------------------------------------------------- CLI
def _parse_models(text: str) -> tuple[str, ...]:
    names = tuple(part.strip() for part in text.split(",") if part.strip())
    if not names:
        raise ValueError("at least one model is required (--models)")
    unknown = [name for name in names if name not in config.MODEL_NAMES]
    if unknown:
        raise ValueError(
            f"unknown model(s) {unknown}; the declared models are {config.MODEL_NAMES}"
        )
    return names


def _parse_assumptions(text: str) -> tuple[str, ...]:
    names = tuple(part.strip() for part in text.split(",") if part.strip())
    if not names:
        raise ValueError("at least one assumption is required (--assumptions)")
    unknown = [name for name in names if name not in SENSITIVITY_ASSUMPTIONS]
    if unknown:
        raise ValueError(
            f"unknown assumption(s) {unknown}; the sweep covers exactly "
            f"{sorted(SENSITIVITY_ASSUMPTIONS)}"
        )
    return names


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sweep the ten pre-declared assumptions of SPEC_V1 11 (SIMULATED data)."
    )
    parser.add_argument("--seed", type=int, default=config.SEEDS[0])
    parser.add_argument("--n-scenarios", type=int, default=250)
    parser.add_argument("--models", default="ridge,hist_gradient_boosting")
    parser.add_argument("--assumptions", default=",".join(SENSITIVITY_ASSUMPTIONS))
    parser.add_argument("--max-iterations", type=int, default=20)
    parser.add_argument("--population-size", type=int, default=8)
    parser.add_argument("--perturbation-draws", type=int, default=20)
    parser.add_argument("--outdir", default=str(config.RESULTS_DIR / "sensitivity"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    models = _parse_models(args.models)
    assumptions = _parse_assumptions(args.assumptions)

    result = run_sensitivity_sweep(
        seed=args.seed,
        n_scenarios=args.n_scenarios,
        model_names=models,
        assumptions=assumptions,
        max_iterations=args.max_iterations,
        population_size=args.population_size,
        perturbation_draws=args.perturbation_draws,
    )
    paths = write_sweep_results(result, args.outdir)

    for assumption in assumptions:
        rows = [row for row in result["rows"] if row["assumption"] == assumption]
        nominal = next(row for row in rows if row["is_nominal"])
        print(
            f"{assumption} ({SENSITIVITY_ASSUMPTIONS[assumption]['label']}): nominal median "
            f"{nominal['median_yield']:.1f} mL/g VS [SIMULATED]"
        )
        for row in rows:
            print(
                f"  {row['level']:>8} -> median {row['median_yield']:.1f} "
                f"({row['median_yield_delta_pct']:+.1f} %), C1 recommendation "
                f"{row['c1_yield']:.1f} ({row['c1_yield_delta_pct']:+.1f} %), "
                f"C1+C2 {row['c1_c2_yield']:.1f} ({row['c1_c2_yield_delta_pct']:+.1f} %) "
                f"[SIMULATED]"
            )
    print(f"warning: {CAVEAT}")
    print(f"wrote {len(paths)} artefacts to {Path(args.outdir)} [SIMULATED]")
    return 0


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
