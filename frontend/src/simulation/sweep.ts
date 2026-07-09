/**
 * Sweep logic — runs the simulation across a range of starting ages
 * with multiple scenarios (natural only, with IVF, with frozen reserves).
 */

import type { SweepRequest, SweepResponse, SweepPoint } from "../api/types";
import { runSimulation } from "./simulation";
import type { SimulationParams } from "./simulation";

const NUM_SIMULATIONS = 5_000;

function buildSweepParams(
  req: SweepRequest,
  femaleAge: number,
  overrides?: {
    ivfWillingness?: string;
    includeFrozen?: boolean;
  },
): SimulationParams {
  const ivfWillingness = (overrides?.ivfWillingness ?? req.ivf_willingness) as SimulationParams["ivfWillingness"];
  const includeFrozen = overrides?.includeFrozen ?? true;

  // Skip history when sweep age is younger than when the event happened
  let priorLiveBirths = req.prior_live_births ?? 0;
  if (req.age_at_last_birth != null && femaleAge < req.age_at_last_birth) {
    priorLiveBirths = 0;
  }

  let priorMiscarriages = req.prior_miscarriages ?? 0;
  if (req.age_at_last_miscarriage != null && femaleAge < req.age_at_last_miscarriage) {
    priorMiscarriages = 0;
  }

  return {
    femaleAge,
    desiredChildren: req.desired_children,
    maleAge: req.male_age_offset != null ? femaleAge + req.male_age_offset : null,
    bmi: req.bmi ?? null,
    ivfWillingness,
    minSpacingMonths: req.min_spacing_months ?? 18,
    priorLiveBirths,
    priorMiscarriages,
    cyclesTried: req.cycles_tried ?? 0,
    cyclesBeforeIvf: req.cycles_before_ivf ?? 12,
    maxIvfCycles: req.max_ivf_cycles ?? 3,
    smokingStatus: req.smoking_status ?? "never",
    frozenEggBatches: includeFrozen ? (req.frozen_egg_batches ?? []) : [],
    frozenEmbryoBatches: includeFrozen ? (req.frozen_embryo_batches ?? []) : [],
    numSimulations: NUM_SIMULATIONS,
  };
}

function runSweepScenario(
  req: SweepRequest,
  agePoints: number[],
  overrides?: {
    ivfWillingness?: string;
    includeFrozen?: boolean;
  },
): SweepPoint[] {
  return agePoints.map((age, i) => {
    const params = buildSweepParams(req, age, overrides);
    const result = runSimulation(params, 42 + i);
    return {
      starting_age: age,
      completion_rate: result.completionRate,
      completion_by_method: result.completionByMethod,
      median_time_months: result.medianTimeToCompletionMonths,
    };
  });
}

export function computeSweep(req: SweepRequest): SweepResponse {
  // Generate age points
  const agePoints: number[] = [];
  const step = req.age_step ?? 1;
  for (let age = req.age_range_start; age <= req.age_range_end + 1e-9; age += step) {
    agePoints.push(Math.round(age * 100) / 100);
  }

  // Main results with user's settings
  const results = runSweepScenario(req, agePoints);

  // Scenarios
  const naturalOnly = runSweepScenario(req, agePoints, {
    ivfWillingness: "no",
    includeFrozen: false,
  });
  const withIvf = runSweepScenario(req, agePoints, {
    ivfWillingness: "yes",
    includeFrozen: false,
  });

  const hasFrozen =
    (req.frozen_egg_batches?.length ?? 0) > 0 ||
    (req.frozen_embryo_batches?.length ?? 0) > 0;
  const withFrozen = hasFrozen
    ? runSweepScenario(req, agePoints, {
        ivfWillingness: "yes",
        includeFrozen: true,
      })
    : null;

  return {
    results,
    scenarios: {
      natural_only: naturalOnly,
      with_ivf: withIvf,
      with_frozen: withFrozen,
    },
  };
}
