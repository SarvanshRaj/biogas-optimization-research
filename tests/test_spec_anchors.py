"""Specification-anchor tests (test matrix group D-SPEC).

`docs/model_specification.md` section 4.1 lists hand-arithmetic sanity values computed in a
scratch session *before* the equations were implemented. These tests pin what the frozen
equations of section 3.2/3.3 actually produce, and record where the scratch values do not
reproduce. See `docs/known_issues.md` for the full comparison; nothing here changes
the frozen specification - it is a verification record.
"""

from __future__ import annotations

import numpy as np
import pytest

from src import config
from src.simulate_data import (
    availability_factor,
    ceiling_ml_per_g_vs,
    f_lcfa,
    f_load,
    f_ph,
    f_tan,
    f_temperature,
    lcfa_concentration,
    loss_fraction,
    ph_effective,
    pretreatment_progress,
    tan_concentration,
    vfa_stress,
    washout_factor,
    yield_endpoint,
)


def _a(value: float) -> np.ndarray:
    return np.array([float(value)])


def anchor_yield(
    c: float,
    p: float,
    lip: float,
    total_solids: float,
    temperature: float,
    ph: float,
    olr: float,
    hrt: float,
    hours: float = 0.0,
    response: float = 1.0,
    loss: float = 0.0,
    inoculum: float = 2.0,
) -> float:
    """Evaluate the frozen yield equation for one configuration (mL CH4 / g VS)."""
    return float(
        yield_endpoint(
            carb=_a(c),
            protein=_a(p),
            lipid=_a(lip),
            total_solids=_a(total_solids),
            temperature=_a(temperature),
            ph=_a(ph),
            olr=_a(olr),
            hrt=_a(hrt),
            inoculum=_a(inoculum),
            pretreatment_hours=_a(hours),
            pretreatment_response=_a(response),
            degradable_mass_loss=_a(loss),
        )[0]
    )


def anchor_variant_b(
    c: float,
    p: float,
    lip: float,
    total_solids: float,
    temperature: float,
    ph: float,
    olr: float,
    hrt: float,
    hours: float = 0.0,
    response: float = 1.0,
    loss: float = 0.0,
) -> float:
    """The alternative reading of section 3.3 rule 1: inhibitors act on the yield only.

    Kept as an executable record of the largest known ambiguity in the frozen text.
    """
    vs = total_solids / 100.0 * config.VS_TS * 1000.0
    progress = pretreatment_progress(hours)
    avail = float(availability_factor(_a(response), progress)[0])
    loss_frac = float(loss_fraction(_a(loss), progress)[0])
    stress = float(vfa_stress(_a(olr), _a(lip), _a(p))[0])
    ph_eff = float(ph_effective(_a(ph), _a(stress))[0])
    f_l = float(f_lcfa(_a(lip * vs * config.ETA_LCFA), config.C_LCFA_HALF)[0])
    f_a = float(f_tan(_a(config.PROTEIN_N_FRACTION * p * vs * config.PROTEIN_N_RELEASE),
                      config.C_TAN_HALF)[0])
    k = config.K_REF * float(f_temperature(_a(temperature))[0]) * float(f_ph(_a(ph_eff))[0]) \
        * avail ** 0.7
    window = 1.0 - np.exp(-k * min(config.DIGESTION_WINDOW_DAYS, hrt))
    return float(
        ceiling_ml_per_g_vs(_a(c), _a(p), _a(lip))[0] * avail * (1.0 - loss_frac) * window
        * f_l * f_a * float(f_load(_a(olr), _a(total_solids))[0]) * float(washout_factor(_a(hrt))[0])
    )


SPEC_ANCHORS: list[tuple[str, float, tuple[float, ...], dict[str, float]]] = [
    # name, spec 4.1 value, arguments
    ("reference_favourable", 412.0, (0.77, 0.15, 0.08, 12.0, 33.5, 7.0, 2.5, 30.0), {}),
    ("typical_mixed_food_waste", 399.0, (0.70, 0.20, 0.10, 12.0, 35.0, 7.0, 2.5, 30.0), {}),
    ("low_lipid_high_carb", 370.0, (0.80, 0.15, 0.05, 8.0, 35.0, 7.0, 2.0, 30.0), {}),
]


@pytest.mark.parametrize("name,spec,args,kwargs", SPEC_ANCHORS)
def test_reproduced_spec_anchors(
    name: str, spec: float, args: tuple[float, ...], kwargs: dict[str, float]
) -> None:
    """These three reproduce the scratch arithmetic to within 1 mL/g VS."""
    assert anchor_yield(*args, **kwargs) == pytest.approx(spec, abs=1.0)


DIVERGENT_ANCHORS: list[tuple[str, float, tuple[float, ...], dict[str, float], float, float]] = [
    # name, spec 4.1 value, arguments, kwargs, literal-code value, variant-B value
    ("lipid_protein_rich_mid_ops", 349.0, (0.55, 0.20, 0.25, 15.0, 35.0, 7.0, 3.0, 20.0), {},
     274.7, 312.0),
    ("high_lipid_high_solids", 217.0, (0.65, 0.05, 0.30, 20.0, 37.0, 7.0, 4.0, 30.0), {},
     191.7, 206.2),
    ("cold_and_acidic", 161.0, (0.77, 0.15, 0.08, 12.0, 20.0, 6.0, 2.5, 30.0), {}, 109.1, 117.2),
    ("pretreatment_harmful_96h", 275.0, (0.77, 0.15, 0.08, 12.0, 33.5, 7.0, 2.5, 30.0),
     {"hours": 96.0, "response": 0.75, "loss": 0.10}, 283.8, 285.2),
    ("pretreatment_neutral_96h", 362.0, (0.77, 0.15, 0.08, 12.0, 33.5, 7.0, 2.5, 30.0),
     {"hours": 96.0, "response": 1.00, "loss": 0.10}, 373.3, 374.3),
    ("pretreatment_beneficial_96h", 466.0, (0.77, 0.15, 0.08, 12.0, 33.5, 7.0, 2.5, 30.0),
     {"hours": 96.0, "response": 1.30, "loss": 0.10}, 479.6, 480.1),
    ("pretreatment_beneficial_24h", 437.0, (0.77, 0.15, 0.08, 12.0, 33.5, 7.0, 2.5, 30.0),
     {"hours": 24.0, "response": 1.30, "loss": 0.10}, 450.0, 450.7),
    ("ood_mild", 131.0, (0.50, 0.15, 0.35, 24.0, 55.0, 7.0, 2.5, 30.0), {}, 124.8, 143.7),
    ("ood_near_edge", 201.0, (0.53, 0.15, 0.32, 22.0, 35.0, 7.0, 2.5, 30.0), {}, 187.1, 202.7),
]


@pytest.mark.parametrize(
    "name,spec,args,kwargs,literal,variant_b", DIVERGENT_ANCHORS, ids=[a[0] for a in DIVERGENT_ANCHORS]
)
def test_divergent_anchor_values_are_pinned(
    name: str,
    spec: float,
    args: tuple[float, ...],
    kwargs: dict[str, float],
    literal: float,
    variant_b: float,
) -> None:
    """Anchors the scratch session could not reproduce: both readings are pinned.

    If either number moves, the divergence changed and `docs/known_issues.md` must be
    revisited. The spec value is asserted to be *unreachable* by the frozen equations so that a
    silent re-calibration cannot make the discrepancy disappear.
    """
    got = anchor_yield(*args, **kwargs)
    alt = anchor_variant_b(*args, **kwargs)
    assert got == pytest.approx(literal, abs=1.0), f"{name}: literal reading moved"
    assert alt == pytest.approx(variant_b, abs=1.5), f"{name}: variant-B reading moved"
    if abs(literal - spec) > 2.0 and abs(variant_b - spec) > 2.0:
        assert abs(got - spec) > 1.0, f"{name}: reproduced after all"


def test_inhibitor_channel_ambiguity_is_bounded() -> None:
    """Section 3.3 rule 1 vs the k equation: quantify the largest reading difference."""
    worst = max(
        abs(anchor_yield(*args, **kwargs) - anchor_variant_b(*args, **kwargs))
        for _, _, args, kwargs, _, _ in DIVERGENT_ANCHORS
    )
    assert worst < 40.0, "the ambiguity grew; re-open the specification"


def test_pretreatment_family_offset_is_small_and_uniform() -> None:
    """The pre-treatment anchors sit ~3 % above the scratch values, on both readings."""
    ratios = []
    for _, spec, args, kwargs, _, _ in DIVERGENT_ANCHORS:
        if not kwargs:  # the pre-treatment family is the only one that overrides hours/R/loss
            continue
        ratios.append(anchor_yield(*args, **kwargs) / spec)
    assert all(1.02 < r < 1.04 for r in ratios), ratios
    assert max(ratios) - min(ratios) < 0.01


def test_mid_range_operations_distribution_anchor() -> None:
    """Section 4.1's distribution anchor (p05/median/p95) across the composition distribution."""
    from src.simulate_data import _sample_composition

    rng = np.random.default_rng(20261007)
    n = 5000
    carb, protein, lipid = _sample_composition(rng, n)
    values = yield_endpoint(
        carb=carb,
        protein=protein,
        lipid=lipid,
        total_solids=np.full(n, 12.0),
        temperature=np.full(n, 35.0),
        ph=np.full(n, 7.0),
        olr=np.full(n, 2.5),
        hrt=np.full(n, 30.0),
        inoculum=np.full(n, 2.0),
        pretreatment_hours=np.zeros(n),
        pretreatment_response=np.ones(n),
        degradable_mass_loss=np.zeros(n),
    )
    assert np.percentile(values, 5) == pytest.approx(388.0, abs=4.0)
    assert float(np.median(values)) == pytest.approx(434.0, abs=4.0)
    assert np.percentile(values, 95) == pytest.approx(490.0, abs=4.0)


def test_upper_tail_caveat_still_holds() -> None:
    """The pre-declared caveat: the simulated tail sits above the measured 348-435 band."""
    from src.simulate_data import _sample_composition

    rng = np.random.default_rng(20261007)
    carb, protein, lipid = _sample_composition(rng, 5000)
    values = ceiling_ml_per_g_vs(carb, protein, lipid)
    assert np.percentile(values, 95) > 435.0


def test_k_ref_rationale_is_a_rate_ratio_not_a_completeness_ratio() -> None:
    """Section 4: f_T(20 C) is ~0.40 of the reference rate, which is what k_ref's note means."""
    assert float(f_temperature(_a(20.0))[0]) == pytest.approx(0.402, abs=0.005)
    k_reference = (
        config.K_REF
        * float(f_temperature(_a(33.5))[0])
        * float(f_ph(_a(7.0))[0])
        * float(f_lcfa(lcfa_concentration(_a(0.08), _a(12.0)), config.C_LCFA_HALF)[0])
        * float(f_tan(tan_concentration(_a(0.15), _a(12.0)), config.C_TAN_HALF)[0])
    )
    completeness = 1.0 - np.exp(-k_reference * 30.0)
    # exact value 0.9930: inside the documented "~95-99 %" statement
    assert 0.95 <= completeness <= 0.995
    # the 30-day window at 20 C is NOT ~40 % complete - the note refers to the rate constant
    assert 1.0 - np.exp(-(k_reference * float(f_temperature(_a(20.0))[0])) * 30.0) > 0.8
