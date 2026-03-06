"""Pydantic request/response models for the fertility forecaster API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .models import (
    FrozenEggBatch,
    FrozenEmbryoBatch,
    SimulationParams,
    SmokingStatus,
)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class FrozenEggBatchIn(BaseModel):
    age_at_freeze: float = Field(ge=18, le=45)
    num_eggs: int = Field(ge=1, le=50)


class FrozenEmbryoBatchIn(BaseModel):
    age_at_freeze: float = Field(ge=18, le=45)
    num_embryos: int = Field(ge=1, le=20)
    pgt_tested: bool = False


class SimulateRequest(BaseModel):
    female_age: float = Field(ge=18, le=45)
    desired_children: int = Field(ge=1, le=6)
    male_age: float | None = Field(default=None, ge=18, le=70)
    bmi: float | None = Field(default=None, ge=10, le=70)
    acceptable_probability: float = Field(default=0.9, ge=0.01, le=1.0)
    ivf_willingness: Literal["yes", "no", "last_resort"] = "no"
    min_spacing_months: int = Field(default=18, ge=6, le=60)
    prior_live_births: int = Field(default=0, ge=0)
    prior_miscarriages: int = Field(default=0, ge=0)
    cycles_tried: int = Field(default=0, ge=0)
    cycles_before_ivf: int = Field(default=12, ge=1, le=60)
    max_ivf_cycles: int = Field(default=3, ge=1, le=10)
    smoking_status: Literal["never", "former", "current_occasional", "current_regular"] = "never"
    frozen_egg_batches: list[FrozenEggBatchIn] = Field(default_factory=list, max_length=5)
    frozen_embryo_batches: list[FrozenEmbryoBatchIn] = Field(
        default_factory=list, max_length=5
    )
    age_at_last_birth: float | None = None
    age_at_last_miscarriage: float | None = None

    @model_validator(mode="after")
    def _check_history_ages(self) -> SimulateRequest:
        if self.age_at_last_birth is not None and self.age_at_last_birth > self.female_age:
            raise ValueError("age_at_last_birth must be <= female_age")
        if (
            self.age_at_last_miscarriage is not None
            and self.age_at_last_miscarriage > self.female_age
        ):
            raise ValueError("age_at_last_miscarriage must be <= female_age")
        return self

    def to_simulation_params(self, **overrides: object) -> SimulationParams:
        """Convert to the core SimulationParams dataclass.

        Accepts **overrides so the sweep endpoint can inject num_simulations,
        female_age, male_age, etc.
        """
        frozen_eggs = tuple(
            FrozenEggBatch(age_at_freeze=b.age_at_freeze, num_eggs=b.num_eggs)
            for b in self.frozen_egg_batches
        )
        frozen_embryos = tuple(
            FrozenEmbryoBatch(
                age_at_freeze=b.age_at_freeze,
                num_embryos=b.num_embryos,
                pgt_tested=b.pgt_tested,
            )
            for b in self.frozen_embryo_batches
        )
        smoking = SmokingStatus(self.smoking_status)

        base = dict(
            female_age=self.female_age,
            desired_children=self.desired_children,
            male_age=self.male_age,
            bmi=self.bmi,
            acceptable_probability=self.acceptable_probability,
            ivf_willingness=self.ivf_willingness,
            min_spacing_months=self.min_spacing_months,
            prior_live_births=self.prior_live_births,
            prior_miscarriages=self.prior_miscarriages,
            cycles_tried=self.cycles_tried,
            cycles_before_ivf=self.cycles_before_ivf,
            max_ivf_cycles=self.max_ivf_cycles,
            smoking_status=smoking,
            frozen_egg_batches=frozen_eggs,
            frozen_embryo_batches=frozen_embryos,
            age_at_last_birth=self.age_at_last_birth,
            age_at_last_miscarriage=self.age_at_last_miscarriage,
        )
        base.update(overrides)
        return SimulationParams(**base)


class SweepRequest(BaseModel):
    age_range_start: float = Field(ge=18, le=45)
    age_range_end: float = Field(ge=18, le=45)
    age_step: float = Field(default=1.0, ge=0.5, le=10)

    desired_children: int = Field(ge=1, le=6)
    male_age_offset: float | None = Field(default=None, ge=-20, le=20)
    bmi: float | None = Field(default=None, ge=10, le=70)
    acceptable_probability: float = Field(default=0.9, ge=0.01, le=1.0)
    ivf_willingness: Literal["yes", "no", "last_resort"] = "no"
    min_spacing_months: int = Field(default=18, ge=6, le=60)
    prior_live_births: int = Field(default=0, ge=0)
    prior_miscarriages: int = Field(default=0, ge=0)
    cycles_tried: int = Field(default=0, ge=0)
    cycles_before_ivf: int = Field(default=12, ge=1, le=60)
    max_ivf_cycles: int = Field(default=3, ge=1, le=10)
    smoking_status: Literal["never", "former", "current_occasional", "current_regular"] = "never"
    frozen_egg_batches: list[FrozenEggBatchIn] = Field(default_factory=list, max_length=5)
    frozen_embryo_batches: list[FrozenEmbryoBatchIn] = Field(
        default_factory=list, max_length=5
    )
    age_at_last_birth: float | None = None
    age_at_last_miscarriage: float | None = None

    @model_validator(mode="after")
    def _check_range(self) -> SweepRequest:
        if self.age_range_end < self.age_range_start:
            raise ValueError("age_range_end must be >= age_range_start")
        return self


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ParamsUsed(BaseModel):
    base_fecundability: float
    curve_type: str
    bmi_natural_fr: float
    bmi_ivf_fr: float
    smoking_fr: float
    sterility_at_start: float


class SimulateResponse(BaseModel):
    completion_rate: float
    median_time_to_completion_months: float | None
    mean_age_at_completion: float | None
    time_distribution: list[float]
    completion_by_method: dict[str, float]
    params_used: ParamsUsed


class SweepPoint(BaseModel):
    starting_age: float
    completion_rate: float
    completion_by_method: dict[str, float]
    median_time_months: float | None


class SweepScenarios(BaseModel):
    natural_only: list[SweepPoint]
    with_ivf: list[SweepPoint]
    with_frozen: list[SweepPoint] | None = None


class SweepResponse(BaseModel):
    results: list[SweepPoint]
    scenarios: SweepScenarios
