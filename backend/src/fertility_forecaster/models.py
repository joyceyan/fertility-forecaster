from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class SmokingStatus(str, Enum):
    NEVER = "never"
    FORMER = "former"
    CURRENT_OCCASIONAL = "current_occasional"
    CURRENT_REGULAR = "current_regular"


@dataclass(frozen=True)
class FrozenEggBatch:
    age_at_freeze: float
    num_eggs: int


@dataclass(frozen=True)
class FrozenEmbryoBatch:
    age_at_freeze: float
    num_embryos: int
    pgt_tested: bool = False


@dataclass(frozen=True)
class SimulationParams:
    """All user inputs for the fertility simulation."""

    female_age: float
    desired_children: int
    male_age: float | None = None
    bmi: float | None = None
    acceptable_probability: float = 0.9
    ivf_willingness: Literal["yes", "no", "last_resort"] = "last_resort"
    min_spacing_months: int = 18
    prior_live_births: int = 0
    prior_miscarriages: int = 0
    cycles_tried: int = 0
    cycles_before_ivf: int = 12
    max_ivf_cycles: int = 3
    smoking_status: SmokingStatus = SmokingStatus.NEVER
    frozen_egg_batches: tuple[FrozenEggBatch, ...] = ()
    frozen_embryo_batches: tuple[FrozenEmbryoBatch, ...] = ()
    age_at_last_birth: float | None = None
    age_at_last_miscarriage: float | None = None
    num_simulations: int = 10_000

    def __post_init__(self) -> None:
        if not 1 <= self.desired_children <= 6:
            raise ValueError("desired_children must be between 1 and 6")
        if not 15 <= self.female_age <= 45:
            raise ValueError("female_age must be in [15, 45]")

    @property
    def max_months(self) -> int:
        return int((50 - self.female_age) * 12) + 1


@dataclass
class SimulationResult:
    """Output of the Monte Carlo simulation."""

    completion_rate: float
    median_time_to_completion_months: float | None
    mean_age_at_completion: float | None
    time_distribution: list[float]
    completion_by_method: dict[str, float]
