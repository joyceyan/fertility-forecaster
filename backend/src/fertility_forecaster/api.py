"""FastAPI application for the fertility forecaster."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import numpy as np
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .curves import (
    _BASE_FECUNDABILITY,
    bmi_fecundability_fr,
    bmi_ivf_adjustment,
    smoking_fecundability_fr,
    sterility_curve,
)
from .models import (
    FrozenEggBatch,
    FrozenEmbryoBatch,
    SmokingStatus,
)
from .schemas import (
    ParamsUsed,
    SimulateRequest,
    SimulateResponse,
    SweepPoint,
    SweepRequest,
    SweepResponse,
    SweepScenarios,
)
from .simulation import run_simulation

logger = logging.getLogger(__name__)

app = FastAPI(title="Fertility Forecaster API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_request_timing(request: Request, call_next):
    start = time.perf_counter()
    response: Response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s %.1fms %s",
        request.method,
        request.url.path,
        elapsed_ms,
        response.status_code,
    )
    return response


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest):
    params = req.to_simulation_params(num_simulations=10_000)
    result = run_simulation(params)

    has_prior = req.prior_live_births > 0 or req.prior_miscarriages > 0
    curve_type = "gravid" if has_prior else "nulligravid"
    smoking = SmokingStatus(req.smoking_status)

    params_used = ParamsUsed(
        base_fecundability=_BASE_FECUNDABILITY,
        curve_type=curve_type,
        bmi_natural_fr=bmi_fecundability_fr(req.bmi),
        bmi_ivf_fr=bmi_ivf_adjustment(req.bmi),
        smoking_fr=smoking_fecundability_fr(smoking),
        sterility_at_start=float(sterility_curve(np.array([req.female_age]))[0]),
    )

    return SimulateResponse(
        completion_rate=result.completion_rate,
        median_time_to_completion_months=result.median_time_to_completion_months,
        mean_age_at_completion=result.mean_age_at_completion,
        time_distribution=result.time_distribution,
        completion_by_method=result.completion_by_method,
        params_used=params_used,
    )


def _build_sweep_params(
    req: SweepRequest,
    female_age: float,
    *,
    ivf_willingness: str | None = None,
    include_frozen: bool = True,
):
    """Build SimulationParams for a single sweep point."""
    overrides: dict = {
        "female_age": female_age,
        "num_simulations": 5_000,
    }

    if ivf_willingness is not None:
        overrides["ivf_willingness"] = ivf_willingness

    if req.male_age_offset is not None:
        overrides["male_age"] = female_age + req.male_age_offset

    # Skip history conditioning when female_age is younger than reported events
    age_at_last_birth = req.age_at_last_birth
    prior_live_births = req.prior_live_births
    if age_at_last_birth is not None and female_age < age_at_last_birth:
        age_at_last_birth = None
        prior_live_births = 0
    overrides["age_at_last_birth"] = age_at_last_birth
    overrides["prior_live_births"] = prior_live_births

    age_at_last_miscarriage = req.age_at_last_miscarriage
    prior_miscarriages = req.prior_miscarriages
    if age_at_last_miscarriage is not None and female_age < age_at_last_miscarriage:
        age_at_last_miscarriage = None
        prior_miscarriages = 0
    overrides["age_at_last_miscarriage"] = age_at_last_miscarriage
    overrides["prior_miscarriages"] = prior_miscarriages

    if not include_frozen:
        overrides["frozen_egg_batches"] = ()
        overrides["frozen_embryo_batches"] = ()

    # Build a temporary SimulateRequest to reuse to_simulation_params
    sim_req = SimulateRequest(
        female_age=female_age,
        desired_children=req.desired_children,
        male_age=overrides.get("male_age", None),
        bmi=req.bmi,
        acceptable_probability=req.acceptable_probability,
        ivf_willingness=overrides.get("ivf_willingness", req.ivf_willingness),
        min_spacing_months=req.min_spacing_months,
        prior_live_births=prior_live_births,
        prior_miscarriages=prior_miscarriages,
        cycles_tried=req.cycles_tried,
        cycles_before_ivf=req.cycles_before_ivf,
        max_ivf_cycles=req.max_ivf_cycles,
        smoking_status=req.smoking_status,
        frozen_egg_batches=req.frozen_egg_batches if include_frozen else [],
        frozen_embryo_batches=req.frozen_embryo_batches if include_frozen else [],
        age_at_last_birth=age_at_last_birth,
        age_at_last_miscarriage=age_at_last_miscarriage,
    )
    return sim_req.to_simulation_params(num_simulations=5_000)


def _run_sweep_scenario(
    req: SweepRequest,
    age_points: list[float],
    *,
    ivf_willingness: str | None = None,
    include_frozen: bool = True,
) -> list[SweepPoint]:
    points: list[SweepPoint] = []
    for i, age in enumerate(age_points):
        params = _build_sweep_params(
            req,
            age,
            ivf_willingness=ivf_willingness,
            include_frozen=include_frozen,
        )
        result = run_simulation(params, seed=42 + i)
        points.append(
            SweepPoint(
                starting_age=age,
                completion_rate=result.completion_rate,
                completion_by_method=result.completion_by_method,
                median_time_months=result.median_time_to_completion_months,
            )
        )
    return points


@app.post("/sweep", response_model=SweepResponse)
def sweep(req: SweepRequest):
    # Generate age points
    age_points: list[float] = []
    age = req.age_range_start
    while age <= req.age_range_end + 1e-9:
        age_points.append(round(age, 2))
        age += req.age_step

    # Main results with user's settings
    results = _run_sweep_scenario(req, age_points)

    # Scenarios
    natural_only = _run_sweep_scenario(
        req, age_points, ivf_willingness="no", include_frozen=False
    )
    with_ivf = _run_sweep_scenario(
        req, age_points, ivf_willingness="yes", include_frozen=False
    )

    has_frozen = len(req.frozen_egg_batches) > 0 or len(req.frozen_embryo_batches) > 0
    with_frozen = None
    if has_frozen:
        with_frozen = _run_sweep_scenario(
            req, age_points, ivf_willingness="yes", include_frozen=True
        )

    return SweepResponse(
        results=results,
        scenarios=SweepScenarios(
            natural_only=natural_only,
            with_ivf=with_ivf,
            with_frozen=with_frozen,
        ),
    )


# ---------------------------------------------------------------------------
# Static files (serves built frontend in production)
# ---------------------------------------------------------------------------

_STATIC_DIR = os.environ.get(
    "STATIC_DIR",
    str(Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist"),
)
if Path(_STATIC_DIR).is_dir():
    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="frontend")
