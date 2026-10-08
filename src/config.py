"""Configuration for the simulated study: the single source of truth for constants.

Everything in this file is frozen by `docs/model_specification.md` (SPEC_V1). Values marked
ASSUMPTION are modelling choices with a declared sensitivity range, not measured quantities.
This module is deliberately dependency-light: it imports nothing from numpy/sklearn/scipy.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- identity
SIMULATOR_VERSION = "SPEC_V1"
DATA_PROVENANCE = "synthetic"
SIMULATED_MARKER = "SIMULATED"
AS_OF = "2026-10-07"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "synthetic"
RESULTS_DIR = PROJECT_ROOT / "results"
MODELS_DIR = RESULTS_DIR / "models"
FIGURES_DIR = RESULTS_DIR / "figures"
DOCS_DIR = PROJECT_ROOT / "docs"

# --------------------------------------------------------------------------- design
SEEDS: tuple[int, ...] = (11, 23, 37, 41, 59)
N_SCENARIOS = 500
N_REPLICATES = 8
N_OOD_SCENARIOS = 60
SPLIT_FRACTIONS = {"train": 0.70, "validation": 0.15, "test": 0.15}
DIGESTION_WINDOW_DAYS = 30.0

TARGET = "simulated_methane_yield_ml_per_g_vs"

# --------------------------------------------------------------------------- columns
FEATURES: tuple[str, ...] = (
    "carb_fraction",
    "protein_fraction",
    "lipid_fraction",
    "total_solids_pct",
    "temperature_c",
    "ph_measured",
    "olr_kg_vs_m3_d",
    "hrt_days",
    "inoculum_ratio",
    "pretreatment_hours",
    "pretreatment_temp_c",
)

LATENT_COLUMNS: tuple[str, ...] = ("pretreatment_response", "degradable_mass_loss")

DIAGNOSTIC_COLUMNS: tuple[str, ...] = (
    "vs_slurry_g_per_l",
    "ph_effective",
    "c_lcfa_g_per_l",
    "tan_g_per_l",
    "f_lcfa",
    "f_tan",
    "rate_constant_per_day",
    "window_completeness",
)

OUTPUT_COLUMNS: tuple[str, ...] = (
    "simulated_methane_fraction",
    TARGET,
    "simulated_biogas_yield_ml_per_g_vs",
    "simulated_stability_indicator",
)

ID_COLUMNS: tuple[str, ...] = ("scenario_id", "replicate_id", "seed", "split")

META_COLUMNS: tuple[str, ...] = ("data_provenance", "simulator_version", "as_of")

FRAME_COLUMNS: tuple[str, ...] = (
    *ID_COLUMNS,
    "carb_fraction",
    "protein_fraction",
    "lipid_fraction",
    "ph_setpoint",
    "total_solids_pct",
    "temperature_c",
    "ph_measured",
    "olr_kg_vs_m3_d",
    "hrt_days",
    "inoculum_ratio",
    "pretreatment_temp_c",
    "pretreatment_hours",
    *DIAGNOSTIC_COLUMNS,
    *OUTPUT_COLUMNS,
    *META_COLUMNS,
)

# --------------------------------------------------------------------------- ranges
#: Model-facing input ranges (SPEC_V1 section 3.1).
INPUT_RANGES: dict[str, tuple[float, float]] = {
    "carb_fraction": (0.45, 0.74),
    "protein_fraction": (0.05, 0.25),
    "lipid_fraction": (0.05, 0.30),
    "total_solids_pct": (5.0, 20.0),
    "temperature_c": (20.0, 60.0),
    "ph_measured": (5.5, 8.5),
    "olr_kg_vs_m3_d": (0.5, 6.0),
    "hrt_days": (10.0, 40.0),
    "inoculum_ratio": (0.5, 4.0),
    "pretreatment_hours": (0.0, 96.0),
    "pretreatment_temp_c": (25.0, 35.0),
}

#: pH setpoint range (decision variable; the realised value is `ph_measured`).
SETPOINT_RANGE: tuple[float, float] = (5.5, 8.5)
INPUT_RANGES["ph_setpoint"] = SETPOINT_RANGE

#: Held-out out-of-distribution family, deliberately outside the training support.
OOD_RANGES: dict[str, tuple[float, float]] = {
    "lipid_fraction": (0.30, 0.38),
    "total_solids_pct": (22.0, 28.0),
    "carb_fraction": (0.40, 0.60),
    "protein_fraction": (0.05, 0.20),
    "temperature_c": (20.0, 60.0),
    "ph_measured": (5.5, 8.5),
    "olr_kg_vs_m3_d": (0.5, 6.0),
    "hrt_days": (10.0, 40.0),
    "inoculum_ratio": (0.5, 4.0),
    "pretreatment_hours": (0.0, 96.0),
    "pretreatment_temp_c": (25.0, 35.0),
}

#: The held-out family extends only two axes (SPEC_V1 8). The remaining axes are sampled
#: inside the CENTRAL part of their normal ranges, not across the whole training range:
#: varying every axis at once makes an extrapolation failure unattributable, and the extreme
#: corners produce near-zero targets (measured: mean 28 mL/g VS, with exact zeros) which makes
#: the reported metrics meaningless. Both variants are reported in
#: `docs/known_issues.md`; this choice was made before any model was trained.
OOD_CENTRAL_BANDS: dict[str, tuple[float, float]] = {
    "temperature_c": (30.0, 55.0),
    "ph_setpoint": (6.5, 7.5),
    "olr_kg_vs_m3_d": (1.5, 4.0),
    "hrt_days": (20.0, 35.0),
    "inoculum_ratio": (1.0, 3.0),
    "pretreatment_hours": (0.0, 96.0),
    "pretreatment_temp_c": (25.0, 35.0),
}

# --------------------------------------------------------------------------- models
MODEL_NAMES: tuple[str, ...] = (
    "dummy",
    "ridge",
    "random_forest",
    "hist_gradient_boosting",
    "mlp",
)

#: Small, pre-declared grids; each entry is a full parameter set (values are floats or tuples).
MODEL_GRIDS: dict[str, list[dict[str, Any]]] = {
    "dummy": [{}],
    "ridge": [{"alpha": 0.1}, {"alpha": 1.0}, {"alpha": 10.0}],
    "random_forest": [
        {"n_estimators": 200, "min_samples_leaf": 1},
        {"n_estimators": 400, "min_samples_leaf": 4},
    ],
    "hist_gradient_boosting": [
        {"learning_rate": 0.05, "max_iter": 300},
        {"learning_rate": 0.1, "max_iter": 200},
    ],
    "mlp": [
        {"hidden_layer_sizes": (32,), "alpha": 1e-4},
        {"hidden_layer_sizes": (64, 32), "alpha": 1e-3},
    ],
}

# --------------------------------------------------------------------------- optimiser
CONSTRAINTS: dict[str, float] = {
    "stability_max": 0.35,
    "tan_max_g_per_l": 4.0,
    "ph_min": 6.5,
    "ph_max": 8.5,
    "hrt_min_days": 12.0,
}

#: Fraction-of-range perturbation used by the robustness harness (±5 %).
PERTURBATION_FRACTION = 0.05

#: Derived (DGP-computed) features that are dependent on a design variable by construction.
#: SPEC_V1 3.2's independence claim is a statement about *sampled* decision variables; features
#: computed inside the data-generating process may legitimately inherit dependence. Anything
#: above the 0.20 design threshold must be listed here with its reason.
DERIVED_CORRELATION_NOTES: dict[str, str] = {
    "ph_measured|olr_kg_vs_m3_d": (
        "pH is drawn down by loading-driven VFA stress (SPEC_V1 3.4), so the realised "
        "measurement is negatively correlated with organic loading. Intended, not a "
        "sampling artefact."
    ),
}

#: Decision tiers (SPEC_V1 section 2, decision S-7).
TIER_C1: tuple[str, ...] = (
    "carb_fraction",
    "protein_fraction",
    "lipid_fraction",
    "total_solids_pct",
    "temperature_c",
    "pretreatment_hours",
    "pretreatment_temp_c",
    "olr_kg_vs_m3_d",
)
TIER_C2: tuple[str, ...] = ("ph_measured", "hrt_days", "inoculum_ratio")

#: Equal-thirds baseline mixture (decision D6) and mid-range process settings.
BASELINE_PROCESS: dict[str, float] = {
    "total_solids_pct": 12.0,
    "temperature_c": 35.0,
    "ph_measured": 7.0,
    "olr_kg_vs_m3_d": 2.5,
    "hrt_days": 30.0,
    "inoculum_ratio": 2.0,
    "pretreatment_hours": 0.0,
    "pretreatment_temp_c": 30.0,
}

# --------------------------------------------------------------------------- generator constants
#: Theoretical methane potentials, L CH4 / g VS. ASSUMPTION (textbook stoichiometry, not
#: retrieved this session); sensitivity +/-15 %.
K_CARB, K_PROT, K_LIP = 0.415, 0.496, 1.014

#: Biodegradability factor. ASSUMPTION, calibrated so the reference configuration lands
#: inside the measured 348-435 mL CH4/g VS band [CIT-0003]. Sensitivity 0.85-1.00.
BETA = 0.95

#: Reference first-order rate constant, 1/day. ASSUMPTION, calibrated (see SPEC_V1 4.1).
K_REF = 0.18

#: Volatile-solids fraction of total solids, from measured 83-87 % [CIT-0003].
VS_TS = 0.85

#: LCFA partition assumption (fraction of lipid appearing as inhibitory LCFA). ASSUMPTION.
ETA_LCFA = 0.012

#: Half-saturation constants. ASSUMPTIONs informed by CIT-0015 (LCFA) and CIT-0014 (TAN).
C_LCFA_HALF = 1.2
C_TAN_HALF = 6.0

#: Protein nitrogen content and release fraction. ASSUMPTIONs.
PROTEIN_N_FRACTION = 0.16
PROTEIN_N_RELEASE = 0.70

#: Temperature response (two optima). Centres sourced; widths are ASSUMPTIONs.
T_MESO_CENTRE, T_MESO_SIGMA = 33.5, 10.0
T_THERMO_CENTRE, T_THERMO_SIGMA = 55.0, 6.5
T_THERMO_AMPLITUDE = 0.98

#: pH plateau (sourced) and decay scale (ASSUMPTION).
PH_LOW, PH_HIGH = 6.8, 7.2
PH_DECAY = 0.7

#: Loading response (mild by design; the TS direction is contested, claim C-005).
OLR_CENTRE, OLR_SIGMA = 2.5, 1.8
TS_CENTRE, TS_SIGMA = 12.0, 10.0

#: Sweep hooks (SPEC_V1 11). Each has a frozen default that reproduces the frozen simulator
#: exactly; `src/sensitivity.py` is the only caller that moves them, inside a context manager,
#: and a test proves the nominal level of every assumption reproduces the committed dataset.
#:   TS_SHAPE  - "peak" is the frozen single-peak form; "monotone" is the declared increasing
#:               form used only by the sweep level that represents CIT-0006's direction.
#:   RESPONSE_CENTRE - centre of the pre-treatment response draw (frozen 1.00 = neutral)
#:   NOISE_SCALE     - multiplier on the two noise sigmas (frozen 1.0)
TS_SHAPE = "peak"
TS_MONOTONE_SCALE = 10.0  # width of the declared monotone TS form, in % TS; ASSUMPTION
RESPONSE_CENTRE = 1.00
NOISE_SCALE = 1.0

#: Pre-treatment kinetics and loss. ASSUMPTIONs.
PRETREATMENT_TAU_H = 36.0
R_LOW, R_HIGH = 0.70, 1.60
LOSS_MAX = 0.20

#: Washout clip (ASSUMPTION).
WASHOUT_HRT_MIN, WASHOUT_HRT_FULL = 6.0, 12.0

#: VFA-stress construct (internal; never a measurement).
VFA_OLR_REF = 3.0
VFA_LIPID_WEIGHT = 0.6
VFA_PROTEIN_WEIGHT = 0.4
PH_DROP_PER_STRESS = 0.8

#: Noise model (SPEC_V1 section 3.5).
SIGMA_SCENARIO = 0.04
SIGMA_REPLICATE = 0.05

#: Output clipping.
YIELD_MIN, YIELD_MAX = 0.0, 600.0

#: Methane fraction model.
METHANE_FRACTION_BASE = 0.50
METHANE_FRACTION_LIPID = 0.65
METHANE_FRACTION_NOISE = 0.01
METHANE_FRACTION_MIN, METHANE_FRACTION_MAX = 0.45, 0.75

#: Missingness (MAR), present so that imputation and leakage guards are exercised.
MISSING_RATE_PH, MISSING_RATE_TEMP = 0.02, 0.015

#: Rounding steps, exactly the columns SPEC_V1 3.6 lists (no other column is rounded).
ROUNDING: dict[str, float] = {
    "ph_measured": 0.1,
    "total_solids_pct": 0.5,
    "temperature_c": 0.5,
    "olr_kg_vs_m3_d": 0.1,
    "yield": 0.1,
}

#: Pre-declared sensitivity grid (SPEC_V1 section 11).
SENSITIVITY_GRID: dict[str, tuple[float, float, float]] = {
    "beta": (0.85, 0.95, 1.00),
    "eta_lcfa": (0.005, 0.012, 0.030),
    "c_lcfa_half": (0.8, 1.2, 2.0),
    "c_tan_half": (4.0, 6.0, 10.0),
    "k_ref": (0.10, 0.18, 0.25),
    "t_meso_sigma": (7.0, 10.0, 14.0),
    "ts_shape": (0.0, 1.0, 2.0),
    "pretreatment_mean": (0.90, 1.00, 1.10),
    "noise_scale": (0.5, 1.0, 2.0),
    "missingness_rate": (0.0, 1.0, 2.5),
}

# --------------------------------------------------------------------------- labelling
SCALE_ADOPTION_NOTE = (
    "SIMULATED quantity. The unit mL CH4/g VS (STP) is a scale adoption from the BMP "
    "reporting convention documented in CIT-0004 (Filer et al. 2019, Water 11(5):921); the "
    "internal computation is scale-free and the unit is applied once, as a declared "
    "conversion. This value is not a measurement."
)
NO_BMP_PROTOCOL_NOTE = (
    "No BMP protocol is implemented: there is no inoculum pre-incubation, no 10 g VS/L "
    "loading rule, no 30-day incubation constraint and no positive control. The simulation "
    "only borrows the reporting unit."
)
