"""Shared pytest fixtures.

Tests are written before the code they exercise. Fixtures that touch `src.*` therefore fail
loudly at import time until the corresponding module exists, which is the intended starting state.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture(scope="session")
def small_frame() -> pd.DataFrame:
    """A small but real generated frame (seed 11, 40 scenarios) for schema-level tests."""
    from src.simulate_data import simulate

    frame, latent = simulate(seed=11, n_scenarios=40)
    assert len(frame) == 40 * 8
    assert len(latent) == 40
    return frame


@pytest.fixture(scope="session")
def two_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Two frames from different seeds, used for seed-dependence tests."""
    from src.simulate_data import simulate

    a, _ = simulate(seed=11, n_scenarios=40)
    b, _ = simulate(seed=23, n_scenarios=40)
    return a, b


@pytest.fixture()
def rng() -> np.random.Generator:
    return np.random.default_rng(12345)
