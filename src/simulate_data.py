"""Synthetic data generator for SPEC_V1.

Every number produced here is SIMULATED. The generator implements the frozen equations of
`docs/model_specification.md`; it is not a model of a real digester and it is not a BMP test.

CLI
---
    python -m src.simulate_data --seed 11 --outdir data/synthetic
    python -m src.simulate_data --all-seeds --outdir data/synthetic
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src import config

# ============================================================================ pure surfaces


def pretreatment_progress(hours: float | np.ndarray) -> float | np.ndarray:
    """Fraction of the asymptotic pre-treatment effect reached after `hours` (0 at 0 h)."""
    hours_arr = np.asarray(hours, dtype=float)
    if np.any(hours_arr < 0.0):
        raise ValueError("pretreatment hours must be non-negative")
    result = 1.0 - np.exp(-hours_arr / config.PRETREATMENT_TAU_H)
    return float(result) if np.ndim(hours) == 0 else result


def availability_factor(
    response: np.ndarray, progress: float | np.ndarray
) -> np.ndarray:
    """Availability multiplier: 1 at no effect, >1 beneficial, <1 harmful."""
    return 1.0 + (np.asarray(response, dtype=float) - 1.0) * progress


def loss_fraction(loss: np.ndarray, progress: float | np.ndarray) -> np.ndarray:
    """Degradable-mass loss fraction (0 at no pre-treatment)."""
    return np.asarray(loss, dtype=float) * progress


def vs_slurry_g_per_l(total_solids: np.ndarray) -> np.ndarray:
    """Volatile solids per litre of slurry, from total solids percent (ASSUMPTION VS/TS)."""
    return np.asarray(total_solids, dtype=float) / 100.0 * config.VS_TS * 1000.0


def ceiling_ml_per_g_vs(carb: np.ndarray, protein: np.ndarray, lipid: np.ndarray) -> np.ndarray:
    """Composition-weighted theoretical methane ceiling, mL CH4 / g VS (ASSUMPTION)."""
    blend = (
        np.asarray(carb, dtype=float) * config.K_CARB
        + np.asarray(protein, dtype=float) * config.K_PROT
        + np.asarray(lipid, dtype=float) * config.K_LIP
    )
    return config.BETA * blend * 1000.0


def f_temperature(temperature: np.ndarray) -> np.ndarray:
    """Two-optimum temperature response (mesophilic centre 33.5 C, thermophilic 55 C)."""
    t = np.asarray(temperature, dtype=float)
    meso = np.exp(-0.5 * ((t - config.T_MESO_CENTRE) / config.T_MESO_SIGMA) ** 2)
    thermo = config.T_THERMO_AMPLITUDE * np.exp(
        -0.5 * ((t - config.T_THERMO_CENTRE) / config.T_THERMO_SIGMA) ** 2
    )
    return np.maximum(meso, thermo)


def f_ph(ph: np.ndarray) -> np.ndarray:
    """Plateau at the sourced optimum band, Gaussian penalty outside it (width ASSUMPTION)."""
    p = np.asarray(ph, dtype=float)
    # Nested maximum instead of np.maximum.reduce([...]): the ufunc's reduce overloads reject a
    # list argument under the numpy 2.5 stubs, which fails the mypy job on Python 3.12.
    distance = np.maximum(np.maximum(p - config.PH_HIGH, config.PH_LOW - p), 0.0)
    return np.exp(-((distance / config.PH_DECAY) ** 2))


def lcfa_concentration(lipid: np.ndarray, total_solids: np.ndarray) -> np.ndarray:
    """Bulk LCFA concentration, g/L (ASSUMPTION partition eta)."""
    return (
        np.asarray(lipid, dtype=float)
        * vs_slurry_g_per_l(total_solids)
        * config.ETA_LCFA
    )


def tan_concentration(protein: np.ndarray, total_solids: np.ndarray) -> np.ndarray:
    """Bulk total ammonia nitrogen, g/L (ASSUMPTION N fraction and release)."""
    return (
        config.PROTEIN_N_FRACTION
        * np.asarray(protein, dtype=float)
        * vs_slurry_g_per_l(total_solids)
        * config.PROTEIN_N_RELEASE
    )


def f_lcfa(concentration: np.ndarray, half: float) -> np.ndarray:
    """Hill-type penalty (n = 2) with the given half-saturation concentration."""
    c = np.asarray(concentration, dtype=float)
    return 1.0 / (1.0 + (c / half) ** 2)


def f_tan(concentration: np.ndarray, half: float) -> np.ndarray:
    """Ammonia penalty, same Hill shape (the threshold spread is carried, not resolved)."""
    c = np.asarray(concentration, dtype=float)
    return 1.0 / (1.0 + (c / half) ** 2)


def f_load(olr: np.ndarray, total_solids: np.ndarray) -> np.ndarray:
    """Mild loading factor (the total-solids direction is contested - claim C-005).

    The loading part is frozen. The total-solids part has two declared forms (SPEC_V1 11,
    assumption 7): the frozen single peak at `TS_CENTRE`, and a monotone increasing form used
    only by the sweep level that represents CIT-0006's direction. The monotone form is a
    *declared* shape, not a fitted curve, and the sweep reports both side by side.
    """
    o = np.asarray(olr, dtype=float)
    ts = np.asarray(total_solids, dtype=float)
    loading = np.exp(-0.5 * ((o - config.OLR_CENTRE) / config.OLR_SIGMA) ** 2)
    if config.TS_SHAPE == "monotone":
        lowest = config.INPUT_RANGES["total_solids_pct"][0]
        solids = 1.0 - np.exp(-(ts - lowest) / config.TS_MONOTONE_SCALE)
    elif config.TS_SHAPE == "peak":
        solids = np.exp(-0.5 * ((ts - config.TS_CENTRE) / config.TS_SIGMA) ** 2)
    else:
        raise ValueError(
            f"unknown TS_SHAPE {config.TS_SHAPE!r}; declared forms are 'peak' (frozen) and "
            "'monotone' (sweep only)"
        )
    return loading * solids


def washout_factor(hrt: np.ndarray) -> np.ndarray:
    """Clipped retention factor: 0 below 6 days, 1 at 12 days and above (ASSUMPTION)."""
    h = np.asarray(hrt, dtype=float)
    return np.clip(
        (h - config.WASHOUT_HRT_MIN) / (config.WASHOUT_HRT_FULL - config.WASHOUT_HRT_MIN),
        0.0,
        1.0,
    )


def vfa_stress(olr: np.ndarray, lipid: np.ndarray, protein: np.ndarray) -> np.ndarray:
    """VFA-accumulation proxy in [0, 1]. An internal construct, never a measurement."""
    o = np.asarray(olr, dtype=float)
    lip = np.asarray(lipid, dtype=float)
    pro = np.asarray(protein, dtype=float)
    raw = (
        (o / config.VFA_OLR_REF)
        * (1.0 + config.VFA_LIPID_WEIGHT * (lip / 0.30))
        * (1.0 + config.VFA_PROTEIN_WEIGHT * (pro / 0.25))
        - 1.0
    )
    return np.clip(raw, 0.0, 1.0)


def ph_effective(ph_setpoint: np.ndarray, stress: np.ndarray) -> np.ndarray:
    """Realised pH after loading-driven acidification."""
    return np.asarray(ph_setpoint, dtype=float) - config.PH_DROP_PER_STRESS * np.asarray(
        stress, dtype=float
    )


def rate_constant(
    temperature: np.ndarray,
    ph: np.ndarray,
    lcfa_factor: np.ndarray,
    tan_factor: np.ndarray,
    availability: np.ndarray,
) -> np.ndarray:
    """First-order rate constant, 1/day: every process factor enters exactly once."""
    return (
        config.K_REF
        * f_temperature(temperature)
        * f_ph(ph)
        * np.asarray(lcfa_factor, dtype=float)
        * np.asarray(tan_factor, dtype=float)
        * np.asarray(availability, dtype=float) ** 0.7
    )


def window_completeness(k: np.ndarray, hrt: np.ndarray) -> np.ndarray:
    """Fraction of the ceiling realised inside min(window, HRT) days."""
    k_arr = np.asarray(k, dtype=float)
    window = np.minimum(config.DIGESTION_WINDOW_DAYS, np.asarray(hrt, dtype=float))
    return 1.0 - np.exp(-k_arr * window)


def yield_endpoint(
    *,
    carb: np.ndarray,
    protein: np.ndarray,
    lipid: np.ndarray,
    total_solids: np.ndarray,
    temperature: np.ndarray,
    ph: np.ndarray,
    olr: np.ndarray,
    hrt: np.ndarray,
    inoculum: np.ndarray,
    pretreatment_hours: np.ndarray,
    pretreatment_response: np.ndarray,
    degradable_mass_loss: np.ndarray,
) -> np.ndarray:
    """SPEC_V1 endpoint yield in mL CH4 / g VS (SIMULATED; see config.SCALE_ADOPTION_NOTE).

    `inoculum` is accepted for interface symmetry with the CSV columns and is deliberately
    **not used**: SPEC_V1 13.1 treats the inoculum-to-substrate ratio as a flat descriptor of
    a digestion setting, and the frozen equation (3.3) contains no inoculum term. A test pins
    this so that a spurious inoculum effect cannot be introduced by accident.
    """
    hours = np.asarray(pretreatment_hours, dtype=float)
    progress = 1.0 - np.exp(-hours / config.PRETREATMENT_TAU_H)
    avail = availability_factor(np.asarray(pretreatment_response, dtype=float), progress)
    loss = loss_fraction(np.asarray(degradable_mass_loss, dtype=float), progress)

    lcfa_c = lcfa_concentration(lipid, total_solids)
    tan_c = tan_concentration(protein, total_solids)
    f_l = f_lcfa(lcfa_c, config.C_LCFA_HALF)
    f_a = f_tan(tan_c, config.C_TAN_HALF)

    stress = vfa_stress(olr, lipid, protein)
    ph_eff = ph_effective(ph, stress)
    k = rate_constant(temperature, ph_eff, f_l, f_a, avail)
    r = window_completeness(k, hrt)

    ceiling_eff = ceiling_ml_per_g_vs(carb, protein, lipid) * avail * (1.0 - loss)
    raw = (
        ceiling_eff
        * r
        * f_l
        * f_a
        * f_load(olr, total_solids)
        * washout_factor(hrt)
    )
    return np.clip(raw, config.YIELD_MIN, config.YIELD_MAX)


# ============================================================================ sampling


def _triangular_inverse(
    u: np.ndarray,
    low: float,
    high: float | np.ndarray,
    mode: float | np.ndarray,
) -> np.ndarray:
    """Inverse CDF of a triangular distribution, vectorised."""
    u = np.asarray(u, dtype=float)
    width = high - low
    split = (mode - low) / width
    left = low + np.sqrt(u * width * (mode - low))
    right = high - np.sqrt((1.0 - u) * width * (high - mode))
    return np.where(u < split, left, right)


def _stratified_uniform(
    rng: np.random.Generator, n: int, low: float, high: float
) -> np.ndarray:
    """Latin-hypercube-style stratified draw on [low, high] (one point per stratum)."""
    u = (rng.permutation(n) + rng.random(n)) / n
    return low + u * (high - low)


def _stratified_triangular(
    rng: np.random.Generator, n: int, low: float, high: float, mode: float
) -> np.ndarray:
    u = (rng.permutation(n) + rng.random(n)) / n
    return _triangular_inverse(u, low, high, mode)


def _sample_composition(
    rng: np.random.Generator, n_scenarios: int, pool_factor: float = 1.8
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sample (carb, protein, lipid) from the declared distribution (decision S-6).

    Lipid is drawn first; carbohydrate is drawn triangularly and truncated so that protein
    can stay at or above its floor; the triple is kept only when protein is inside its range.
    Realised support: lipid [0.05, 0.30], carbohydrate [0.47, 0.74], protein [0.05, 0.25].
    """
    pool = int(np.ceil(n_scenarios * pool_factor))
    lipid = _stratified_triangular(rng, pool, 0.05, 0.30, 0.15)
    upper = np.maximum(np.minimum(0.74, 1.0 - lipid - 0.05), 0.47)
    mode = np.minimum(0.65, upper)
    carb = _triangular_inverse(
        (rng.permutation(pool) + rng.random(pool)) / pool, 0.45, upper, mode
    )
    protein = 1.0 - lipid - carb
    keep = (protein >= 0.05) & (protein <= 0.25)
    if keep.sum() < n_scenarios:
        raise RuntimeError(
            "composition rejection left too few scenarios; increase pool_factor"
        )
    idx = np.flatnonzero(keep)[:n_scenarios]
    return carb[idx], protein[idx], lipid[idx]


def assign_split(scenario_ids: np.ndarray, seed: int) -> np.ndarray:
    """Deterministic scenario-grouped split labels (70/15/15)."""
    ids = np.asarray(scenario_ids)
    unique = np.unique(ids)
    rng = np.random.default_rng(seed + 991)
    order = rng.permutation(len(unique))
    shuffled = unique[order]
    n = len(unique)
    n_train = round(n * config.SPLIT_FRACTIONS["train"])
    n_val = round(n * config.SPLIT_FRACTIONS["validation"])
    labels = np.empty(n, dtype=object)
    labels[order[:n_train]] = "train"
    labels[order[n_train : n_train + n_val]] = "validation"
    labels[order[n_train + n_val :]] = "test"
    mapping = pd.Series(labels, index=shuffled)
    return mapping.reindex(ids).to_numpy()


def _round_to_step(values: np.ndarray, step: float) -> np.ndarray:
    return np.round(np.asarray(values, dtype=float) / step) * step


# ============================================================================ generation


def simulate(seed: int, n_scenarios: int = config.N_SCENARIOS) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate the model-facing frame and the latent-factor frame for one seed."""
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an int")
    if isinstance(n_scenarios, bool) or not isinstance(n_scenarios, int):
        raise TypeError("n_scenarios must be an int")
    if n_scenarios <= 0:
        raise ValueError("n_scenarios must be positive")

    rng = np.random.default_rng(seed)
    carb, protein, lipid = _sample_composition(rng, n_scenarios)

    hours = _stratified_uniform(rng, n_scenarios, *config.INPUT_RANGES["pretreatment_hours"])
    pre_temp = _stratified_uniform(rng, n_scenarios, *config.INPUT_RANGES["pretreatment_temp_c"])
    total_solids = _stratified_uniform(rng, n_scenarios, *config.INPUT_RANGES["total_solids_pct"])
    temperature = _stratified_uniform(rng, n_scenarios, *config.INPUT_RANGES["temperature_c"])
    ph_setpoint = _stratified_uniform(rng, n_scenarios, *config.SETPOINT_RANGE)
    olr = _stratified_uniform(rng, n_scenarios, *config.INPUT_RANGES["olr_kg_vs_m3_d"])
    hrt = _stratified_uniform(rng, n_scenarios, *config.INPUT_RANGES["hrt_days"])
    inoculum = _stratified_uniform(rng, n_scenarios, *config.INPUT_RANGES["inoculum_ratio"])

    response = np.clip(
        config.RESPONSE_CENTRE + (rng.random(n_scenarios) - 0.5) * 0.90,
        config.R_LOW,
        config.R_HIGH,
    )
    mass_loss = _stratified_uniform(rng, n_scenarios, 0.0, config.LOSS_MAX)

    stress = vfa_stress(olr, lipid, protein)
    ph_eff = ph_effective(ph_setpoint, stress)
    lcfa_c = lcfa_concentration(lipid, total_solids)
    tan_c = tan_concentration(protein, total_solids)
    f_l = f_lcfa(lcfa_c, config.C_LCFA_HALF)
    f_a = f_tan(tan_c, config.C_TAN_HALF)
    progress = 1.0 - np.exp(-hours / config.PRETREATMENT_TAU_H)
    avail = 1.0 + (response - 1.0) * progress
    k = rate_constant(temperature, ph_eff, f_l, f_a, avail)
    r_window = window_completeness(k, hrt)

    deterministic = yield_endpoint(
        carb=carb,
        protein=protein,
        lipid=lipid,
        total_solids=total_solids,
        temperature=temperature,
        ph=ph_eff,
        olr=olr,
        hrt=hrt,
        inoculum=inoculum,
        pretreatment_hours=hours,
        pretreatment_response=response,
        degradable_mass_loss=mass_loss,
    )

    reps = config.N_REPLICATES
    n_rows = n_scenarios * reps
    scenario_noise = rng.normal(0.0, config.SIGMA_SCENARIO * config.NOISE_SCALE, size=n_scenarios)
    replicate_noise = rng.normal(0.0, config.SIGMA_REPLICATE * config.NOISE_SCALE, size=n_rows)

    deterministic_rows = np.repeat(deterministic, reps)
    yield_rows = deterministic_rows * np.exp(
        np.repeat(scenario_noise, reps) + replicate_noise
    )
    yield_rows = np.clip(yield_rows, config.YIELD_MIN, config.YIELD_MAX)
    yield_rows = _round_to_step(yield_rows, 0.1)

    methane_fraction = np.clip(
        config.METHANE_FRACTION_BASE
        + config.METHANE_FRACTION_LIPID * np.repeat(lipid, reps)
        + rng.normal(0.0, config.METHANE_FRACTION_NOISE, size=n_rows),
        config.METHANE_FRACTION_MIN,
        config.METHANE_FRACTION_MAX,
    )


    ph_measured = _round_to_step(
        np.clip(np.repeat(ph_eff, reps) + rng.normal(0.0, 0.05, size=n_rows), 5.5, 8.5), 0.1
    )
    missing_ph = rng.choice(n_rows, size=round(config.MISSING_RATE_PH * n_rows), replace=False)
    ph_measured[missing_ph] = np.nan

    temperature_recorded = _round_to_step(np.repeat(temperature, reps), 0.5)
    missing_t = rng.choice(
        n_rows, size=round(config.MISSING_RATE_TEMP * n_rows), replace=False
    )
    temperature_recorded[missing_t] = np.nan

    scenario_ids = np.array([f"S{i:05d}" for i in range(n_scenarios)])
    frame = pd.DataFrame(
        {
            "scenario_id": np.repeat(scenario_ids, reps),
            "replicate_id": np.tile(np.arange(reps), n_scenarios),
            "seed": seed,
            "split": assign_split(np.repeat(scenario_ids, reps), seed),
            "carb_fraction": np.repeat(carb, reps),
            "protein_fraction": np.repeat(protein, reps),
            "lipid_fraction": np.repeat(lipid, reps),
            "ph_setpoint": np.repeat(ph_setpoint, reps),
            "total_solids_pct": _round_to_step(np.repeat(total_solids, reps), 0.5),
            "temperature_c": temperature_recorded,
            "ph_measured": ph_measured,
            "olr_kg_vs_m3_d": _round_to_step(np.repeat(olr, reps), 0.1),
            "hrt_days": np.repeat(hrt, reps),
            "inoculum_ratio": np.repeat(inoculum, reps),
            "pretreatment_temp_c": np.repeat(pre_temp, reps),
            "pretreatment_hours": np.repeat(hours, reps),
            "vs_slurry_g_per_l": np.repeat(vs_slurry_g_per_l(total_solids), reps),
            "ph_effective": np.repeat(ph_eff, reps),
            "c_lcfa_g_per_l": np.repeat(lcfa_c, reps),
            "tan_g_per_l": np.repeat(tan_c, reps),
            "f_lcfa": np.repeat(f_l, reps),
            "f_tan": np.repeat(f_a, reps),
            "rate_constant_per_day": np.repeat(k, reps),
            "window_completeness": np.repeat(r_window, reps),
            "simulated_methane_fraction": methane_fraction,
            config.TARGET: yield_rows,
            "simulated_biogas_yield_ml_per_g_vs": yield_rows / methane_fraction,
            "simulated_stability_indicator": np.repeat(stress, reps),
            "data_provenance": config.DATA_PROVENANCE,
            "simulator_version": config.SIMULATOR_VERSION,
            "as_of": config.AS_OF,
        }
    )[list(config.FRAME_COLUMNS)]

    latent = pd.DataFrame(
        {
            "scenario_id": scenario_ids,
            "seed": seed,
            "pretreatment_response": response,
            "degradable_mass_loss": mass_loss,
            "realised_availability": avail,
            "as_of": config.AS_OF,
        }
    )
    return frame, latent


def simulate_ood(
    seed: int, n_scenarios: int = config.N_OOD_SCENARIOS, _pool_factor: float = 1.6
) -> pd.DataFrame:
    """Held-out out-of-distribution family: outside the training support on two axes.

    The remaining axes stay inside a central band of their normal ranges
    (`config.OOD_CENTRAL_BANDS`); see `docs/known_issues.md` for why.
    """
    rng = np.random.default_rng(seed + 5000)
    pool = int(np.ceil(n_scenarios * _pool_factor))
    lipid = _stratified_uniform(rng, pool, *config.OOD_RANGES["lipid_fraction"])
    protein = _stratified_uniform(rng, pool, *config.OOD_RANGES["protein_fraction"])
    carb = 1.0 - lipid - protein
    keep = (carb >= config.OOD_RANGES["carb_fraction"][0]) & (
        carb <= config.OOD_RANGES["carb_fraction"][1]
    )
    if keep.sum() < n_scenarios:
        raise RuntimeError("held-out sampler rejected too many draws; widen the pool factor")
    idx = np.flatnonzero(keep)[:n_scenarios]
    lipid, protein, carb = lipid[idx], protein[idx], carb[idx]
    total_solids = _stratified_uniform(rng, n_scenarios, *config.OOD_RANGES["total_solids_pct"])
    bands = config.OOD_CENTRAL_BANDS
    temperature = _stratified_uniform(rng, n_scenarios, *bands["temperature_c"])
    ph_setpoint = _stratified_uniform(rng, n_scenarios, *bands["ph_setpoint"])
    olr = _stratified_uniform(rng, n_scenarios, *bands["olr_kg_vs_m3_d"])
    hrt = _stratified_uniform(rng, n_scenarios, *bands["hrt_days"])
    inoculum = _stratified_uniform(rng, n_scenarios, *bands["inoculum_ratio"])
    hours = _stratified_uniform(rng, n_scenarios, *bands["pretreatment_hours"])
    pre_temp = _stratified_uniform(rng, n_scenarios, *bands["pretreatment_temp_c"])
    response = np.clip(
        config.RESPONSE_CENTRE + (rng.random(n_scenarios) - 0.5) * 0.90,
        config.R_LOW,
        config.R_HIGH,
    )
    mass_loss = _stratified_uniform(rng, n_scenarios, 0.0, config.LOSS_MAX)

    stress = vfa_stress(olr, lipid, protein)
    ph_eff = ph_effective(ph_setpoint, stress)
    lcfa_c = lcfa_concentration(lipid, total_solids)
    tan_c = tan_concentration(protein, total_solids)
    f_l = f_lcfa(lcfa_c, config.C_LCFA_HALF)
    f_a = f_tan(tan_c, config.C_TAN_HALF)
    progress = 1.0 - np.exp(-hours / config.PRETREATMENT_TAU_H)
    avail = 1.0 + (response - 1.0) * progress
    k = rate_constant(temperature, ph_eff, f_l, f_a, avail)
    deterministic = yield_endpoint(
        carb=carb,
        protein=protein,
        lipid=lipid,
        total_solids=total_solids,
        temperature=temperature,
        ph=ph_eff,
        olr=olr,
        hrt=hrt,
        inoculum=inoculum,
        pretreatment_hours=hours,
        pretreatment_response=response,
        degradable_mass_loss=mass_loss,
    )
    reps = config.N_REPLICATES
    n_rows = n_scenarios * reps
    scenario_noise = rng.normal(0.0, config.SIGMA_SCENARIO * config.NOISE_SCALE, size=n_scenarios)
    replicate_noise = rng.normal(0.0, config.SIGMA_REPLICATE * config.NOISE_SCALE, size=n_rows)
    values = np.clip(
        np.repeat(deterministic, reps)
        * np.exp(np.repeat(scenario_noise, reps) + replicate_noise),
        config.YIELD_MIN,
        config.YIELD_MAX,
    )
    methane_fraction = np.clip(
        config.METHANE_FRACTION_BASE
        + config.METHANE_FRACTION_LIPID * np.repeat(lipid, reps)
        + rng.normal(0.0, config.METHANE_FRACTION_NOISE, size=n_rows),
        config.METHANE_FRACTION_MIN,
        config.METHANE_FRACTION_MAX,
    )
    ids = np.array([f"OOD{i:05d}" for i in range(n_scenarios)])
    return pd.DataFrame(
        {
            "scenario_id": np.repeat(ids, reps),
            "replicate_id": np.tile(np.arange(reps), n_scenarios),
            "seed": seed,
            "split": "ood",
            "carb_fraction": np.repeat(carb, reps),
            "protein_fraction": np.repeat(protein, reps),
            "lipid_fraction": np.repeat(lipid, reps),
            "ph_setpoint": np.repeat(ph_setpoint, reps),
            "total_solids_pct": np.repeat(total_solids, reps),
            "temperature_c": np.repeat(temperature, reps),
            "ph_measured": _round_to_step(np.clip(np.repeat(ph_eff, reps), 5.5, 8.5), 0.1),
            "olr_kg_vs_m3_d": np.repeat(olr, reps),
            "hrt_days": np.repeat(hrt, reps),
            "inoculum_ratio": np.repeat(inoculum, reps),
            "pretreatment_temp_c": np.repeat(pre_temp, reps),
            "pretreatment_hours": np.repeat(hours, reps),
            "vs_slurry_g_per_l": np.repeat(vs_slurry_g_per_l(total_solids), reps),
            "ph_effective": np.repeat(ph_eff, reps),
            "c_lcfa_g_per_l": np.repeat(lcfa_c, reps),
            "tan_g_per_l": np.repeat(tan_c, reps),
            "f_lcfa": np.repeat(f_l, reps),
            "f_tan": np.repeat(f_a, reps),
            "rate_constant_per_day": np.repeat(k, reps),
            "window_completeness": np.repeat(window_completeness(k, hrt), reps),
            "simulated_methane_fraction": methane_fraction,
            config.TARGET: _round_to_step(values, 0.1),
            "simulated_biogas_yield_ml_per_g_vs": _round_to_step(values, 0.1) / methane_fraction,
            "simulated_stability_indicator": np.repeat(stress, reps),
            "data_provenance": config.DATA_PROVENANCE,
            "simulator_version": config.SIMULATOR_VERSION,
            "as_of": config.AS_OF,
        }
    )[list(config.FRAME_COLUMNS)]


# ============================================================================ validation


def validate_frame(
    frame: pd.DataFrame,
    ranges: dict[str, tuple[float, float]] | None = None,
) -> dict[str, Any]:
    """Check schema, ranges, non-negativity and internal consistency of a generated frame.

    `ranges` defaults to the training envelope (`config.INPUT_RANGES`). The held-out family is
    validated against `config.OOD_RANGES`, because by construction it lies outside the training
    envelope - that is the point of it.
    """
    envelope = config.INPUT_RANGES if ranges is None else ranges
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("frame must be a pandas DataFrame")
    if frame.empty:
        raise ValueError("frame is empty")

    failed: list[str] = []
    if np.isinf(frame.select_dtypes(include=[float]).to_numpy()).any():
        failed.append("non-finite value present")

    if config.TARGET not in frame.columns:
        failed.append(f"{config.TARGET}: missing column")

    for name, (low, high) in envelope.items():
        if name not in frame.columns:
            failed.append(f"{name}: missing column")
            continue
        col = frame[name].dropna()
        if col.min() < low - 1e-9 or col.max() > high + 1e-9:
            failed.append(f"{name}: outside [{low}, {high}]")

    if {"carb_fraction", "protein_fraction", "lipid_fraction"} <= set(frame.columns):
        total = (
            frame["carb_fraction"] + frame["protein_fraction"] + frame["lipid_fraction"]
        )
        if not np.allclose(total.to_numpy(), 1.0, atol=1e-9):
            failed.append("composition does not sum to one")

    if config.TARGET in frame.columns:
        target = frame[config.TARGET]
        if target.min() < config.YIELD_MIN - 1e-9 or target.max() > config.YIELD_MAX + 1e-9:
            failed.append(f"{config.TARGET}: outside physical bounds")
        if target.isna().any():
            failed.append(f"{config.TARGET}: contains missing values")

    if "simulated_stability_indicator" in frame.columns:
        col = frame["simulated_stability_indicator"]
        if col.min() < -1e-9 or col.max() > 1.0 + 1e-9:
            failed.append("stability indicator outside [0, 1]")

    if (
        {config.TARGET, "simulated_biogas_yield_ml_per_g_vs", "simulated_methane_fraction"}
        <= set(frame.columns)
    ):
        recomputed = (
            frame["simulated_biogas_yield_ml_per_g_vs"] * frame["simulated_methane_fraction"]
        )
        if not np.allclose(recomputed.to_numpy(), frame[config.TARGET].to_numpy(), atol=0.5):
            failed.append("mass balance breach between biogas, fraction and yield")

    return {
        "ok": not failed,
        "checks_failed": failed,
        "n_rows": len(frame),
        "n_scenarios": int(frame["scenario_id"].nunique()) if "scenario_id" in frame else 0,
        "envelope": "ood" if ranges is config.OOD_RANGES else "training",
    }


def write_dataset(
    frame: pd.DataFrame,
    latent: pd.DataFrame,
    outdir: Path | str,
    seed: int,
) -> dict[str, Path]:
    """Write the frame, the latent factors and a metadata sidecar. Returns the paths."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    frame_path = outdir / f"foodwaste_biogas_seed{seed}.csv"
    latent_path = outdir / f"latent_factors_seed{seed}.csv"
    meta_path = outdir / f"metadata_seed{seed}.json"
    frame.to_csv(frame_path, index=False)
    if latent is not None and not latent.empty:
        # the latent table is published too, so it carries the same provenance labels as the
        # model-facing frame; a per-row marker costs two constant columns and removes any
        # ambiguity about what this file is
        labelled = latent.copy()
        labelled["data_provenance"] = config.DATA_PROVENANCE
        labelled["simulator_version"] = config.SIMULATOR_VERSION
        labelled.to_csv(latent_path, index=False)
    meta = {
        "data_provenance": config.DATA_PROVENANCE,
        "simulator_version": config.SIMULATOR_VERSION,
        "marker": config.SIMULATED_MARKER,
        "seed": seed,
        "n_rows": len(frame),
        "n_scenarios": int(frame["scenario_id"].nunique()),
        "n_replicates": config.N_REPLICATES,
        "as_of": config.AS_OF,
        "scale_adoption_note": config.SCALE_ADOPTION_NOTE,
        "bmp_protocol": config.NO_BMP_PROTOCOL_NOTE,
        "source": "docs/model_specification.md (SPEC_V1)",
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"frame": frame_path, "latent": latent_path, "metadata": meta_path}


# ============================================================================ CLI


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.simulate_data",
        description="Generate SIMULATED two-stage food-waste-to-biogas datasets (SPEC_V1).",
    )
    parser.add_argument("--seed", type=int, default=config.SEEDS[0])
    parser.add_argument("--n-scenarios", type=int, default=config.N_SCENARIOS)
    parser.add_argument("--outdir", type=Path, default=config.DATA_DIR)
    parser.add_argument("--all-seeds", action="store_true")
    parser.add_argument("--ood", action="store_true", help="also write the held-out OOD family")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    seeds = list(config.SEEDS) if args.all_seeds else [args.seed]
    for seed in seeds:
        frame, latent = simulate(seed=seed, n_scenarios=args.n_scenarios)
        report = validate_frame(frame)
        if not report["ok"]:
            raise SystemExit(f"validation failed for seed {seed}: {report['checks_failed']}")
        paths = write_dataset(frame, latent, args.outdir, seed)
        print(
            f"seed {seed}: wrote {paths['frame']} ({report['n_rows']} rows, "
            f"{report['n_scenarios']} scenarios) [SIMULATED]"
        )
        if args.ood:
            ood = simulate_ood(seed=seed)
            ood_report = validate_frame(ood, ranges=config.OOD_RANGES)
            if not ood_report["ok"]:
                raise SystemExit(f"held-out validation failed: {ood_report['checks_failed']}")
            ood_path = Path(args.outdir) / f"foodwaste_biogas_ood_seed{seed}.csv"
            ood.to_csv(ood_path, index=False)
            print(
                f"seed {seed}: wrote {ood_path} ({len(ood)} rows, held-out OOD outside the "
                f"training envelope) [SIMULATED]"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
