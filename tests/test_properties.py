"""Property-based tests (Hypothesis): test matrix group HYP-1..6.

Properties are stated so they would hold for *any* honest implementation of SPEC_V1, not
just for the one that happens to exist.
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src import config

FRACTIONS = st.floats(min_value=0.01, max_value=0.90, allow_nan=False, allow_infinity=False)
TS = st.floats(min_value=5.0, max_value=20.0, allow_nan=False, allow_infinity=False)
TEMP = st.floats(min_value=15.0, max_value=65.0, allow_nan=False, allow_infinity=False)
PH = st.floats(min_value=4.5, max_value=9.5, allow_nan=False, allow_infinity=False)
OLR = st.floats(min_value=0.1, max_value=8.0, allow_nan=False, allow_infinity=False)
HRT = st.floats(min_value=5.0, max_value=60.0, allow_nan=False, allow_infinity=False)
HOURS = st.floats(min_value=0.0, max_value=200.0, allow_nan=False, allow_infinity=False)
RESPONSE = st.floats(min_value=0.5, max_value=2.0, allow_nan=False, allow_infinity=False)


def _composition(carb: float, protein: float) -> tuple[float, float, float]:
    """Renormalise an arbitrary triple to a valid simplex point."""
    lipid = max(0.02, 1.0 - carb - protein)
    total = carb + protein + lipid
    return carb / total, protein / total, lipid / total


@given(
    carb=FRACTIONS,
    protein=FRACTIONS,
    total_solids=TS,
    temperature=TEMP,
    ph=PH,
    olr=OLR,
    hrt=HRT,
    hours=HOURS,
    response=RESPONSE,
)
@settings(max_examples=150, deadline=None)
def test_yield_is_finite_and_within_bounds(
    carb: float,
    protein: float,
    total_solids: float,
    temperature: float,
    ph: float,
    olr: float,
    hrt: float,
    hours: float,
    response: float,
) -> None:
    from src.simulate_data import yield_endpoint

    c, p, lip = _composition(carb, protein)
    out = yield_endpoint(
        carb=np.array([c]),
        protein=np.array([p]),
        lipid=np.array([lip]),
        total_solids=np.array([total_solids]),
        temperature=np.array([temperature]),
        ph=np.array([ph]),
        olr=np.array([olr]),
        hrt=np.array([hrt]),
        inoculum=np.array([2.0]),
        pretreatment_hours=np.array([hours]),
        pretreatment_response=np.array([response]),
        degradable_mass_loss=np.array([0.10]),
    )[0]
    assert np.isfinite(out)
    assert 0.0 <= out <= config.YIELD_MAX


@given(hours=HOURS, response=RESPONSE)
@settings(max_examples=100, deadline=None)
def test_pretreatment_progress_is_monotone(hours: float, response: float) -> None:
    from src.simulate_data import availability_factor, pretreatment_progress

    g = pretreatment_progress(hours)
    assert 0.0 <= g <= 1.0
    avail = availability_factor(np.array([response]), g)[0]
    assert np.isfinite(avail) and avail > 0.0
    if response >= 1.0:
        assert avail >= 1.0 - 1e-12
    else:
        assert avail <= 1.0 + 1e-12


@given(hours=HOURS)
@settings(max_examples=50, deadline=None)
def test_more_pretreatment_time_never_reduces_progress(hours: float) -> None:
    from src.simulate_data import pretreatment_progress

    assert pretreatment_progress(hours + 1.0) >= pretreatment_progress(hours)


@given(lipid=st.floats(min_value=0.0, max_value=0.5), ts=TS)
@settings(max_examples=100, deadline=None)
def test_lcfa_penalty_is_bounded_and_decreasing(lipid: float, ts: float) -> None:
    from src.simulate_data import f_lcfa, lcfa_concentration

    conc = lcfa_concentration(np.array([lipid]), np.array([ts]))[0]
    factor = f_lcfa(np.array([conc]), config.C_LCFA_HALF)[0]
    assert 0.0 < factor <= 1.0
    higher = f_lcfa(np.array([conc * 2.0 + 1e-9]), config.C_LCFA_HALF)[0]
    assert higher <= factor + 1e-12


@given(carb=FRACTIONS, protein=FRACTIONS, olr=OLR)
@settings(max_examples=100, deadline=None)
def test_vfa_stress_bounded_for_any_input(carb: float, protein: float, olr: float) -> None:
    from src.simulate_data import vfa_stress

    _c, p, lip = _composition(carb, protein)
    s = vfa_stress(np.array([olr]), np.array([lip]), np.array([p]))[0]
    assert 0.0 <= s <= 1.0


@given(
    carb=FRACTIONS,
    protein=FRACTIONS,
    total_solids=TS,
    temperature=TEMP,
    ph=PH,
    olr=OLR,
    hrt=HRT,
)
@settings(max_examples=100, deadline=None)
def test_fixed_inputs_give_identical_outputs(
    carb: float,
    protein: float,
    total_solids: float,
    temperature: float,
    ph: float,
    olr: float,
    hrt: float,
) -> None:
    """Determinism is a property of the surface, independent of the sampler."""
    from src.simulate_data import yield_endpoint

    c, p, lip = _composition(carb, protein)
    kwargs = dict(
        carb=np.array([c]),
        protein=np.array([p]),
        lipid=np.array([lip]),
        total_solids=np.array([total_solids]),
        temperature=np.array([temperature]),
        ph=np.array([ph]),
        olr=np.array([olr]),
        hrt=np.array([hrt]),
        inoculum=np.array([2.0]),
        pretreatment_hours=np.array([0.0]),
        pretreatment_response=np.array([1.0]),
        degradable_mass_loss=np.array([0.0]),
    )
    assert yield_endpoint(**kwargs)[0] == pytest.approx(yield_endpoint(**kwargs)[0], rel=0, abs=0)


@given(ts=TS, hrt=HRT)
@settings(max_examples=50, deadline=None)
def test_washout_and_window_are_bounded(ts: float, hrt: float) -> None:
    from src.simulate_data import washout_factor

    w = washout_factor(np.array([hrt]))[0]
    assert 0.0 <= w <= 1.0
