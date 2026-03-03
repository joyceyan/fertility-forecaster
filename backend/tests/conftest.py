"""Shared fixtures for fertility forecaster tests."""

import numpy as np
import pytest

from fertility_forecaster.models import (
    FrozenEggBatch,
    FrozenEmbryoBatch,
    SimulationParams,
)


@pytest.fixture
def rng():
    return np.random.default_rng(42)


@pytest.fixture
def young_one_child():
    """25-year-old wanting 1 child, defaults otherwise."""
    return SimulationParams(female_age=25, desired_children=1)


@pytest.fixture
def thirty_two_children():
    """30-year-old wanting 2 children."""
    return SimulationParams(female_age=30, desired_children=2)


@pytest.fixture
def old_two_children():
    """42-year-old wanting 2 children."""
    return SimulationParams(female_age=42, desired_children=2)


@pytest.fixture
def with_ivf():
    """35-year-old willing to do IVF, wanting 1 child."""
    return SimulationParams(
        female_age=35, desired_children=1, ivf_willingness="yes"
    )


@pytest.fixture
def with_frozen_eggs():
    """38-year-old with frozen eggs (froze at 30), wanting 1 child."""
    return SimulationParams(
        female_age=38,
        desired_children=1,
        frozen_egg_batches=(FrozenEggBatch(age_at_freeze=30.0, num_eggs=20),),
        ivf_willingness="yes",
    )


@pytest.fixture
def with_frozen_embryos():
    """38-year-old with frozen embryos (created at 30), wanting 1 child."""
    return SimulationParams(
        female_age=38,
        desired_children=1,
        frozen_embryo_batches=(FrozenEmbryoBatch(age_at_freeze=30.0, num_embryos=5),),
        ivf_willingness="yes",
    )
