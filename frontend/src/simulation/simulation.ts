/**
 * Monte Carlo fertility simulation engine.
 *
 * Runs N couples through cycle-by-cycle simulation of natural conception,
 * IVF, and frozen egg/embryo pathways.
 */

import type { SmokingStatus, FrozenEggBatch, FrozenEmbryoBatch } from "../api/types";
import {
  ART_MISCARRIAGE_RATE,
  FECUNDABILITY_CONCENTRATION,
  OOCYTE_SURVIVAL_RATE,
  applyOddsRatio,
  bmiFecundabilityFr,
  bmiIvfAdjustment,
  fecundabilityCurve,
  frozenEggPerOocyteRate,
  frozenEmbryoTransferRate,
  frozenEmbryoTransferRatePgt,
  ivfSuccessRate,
  maleAgeMiscarriageOr,
  miscarriageCurve,
  recurrentMiscarriageOr,
  smokingFecundabilityFr,
} from "./curves";
import { PRNG } from "./prng";

export interface SimulationParams {
  femaleAge: number;
  desiredChildren: number;
  maleAge: number | null;
  bmi: number | null;
  ivfWillingness: "yes" | "no" | "last_resort";
  minSpacingMonths: number;
  priorLiveBirths: number;
  priorMiscarriages: number;
  cyclesTried: number;
  cyclesBeforeIvf: number;
  maxIvfCycles: number;
  smokingStatus: SmokingStatus;
  frozenEggBatches: FrozenEggBatch[];
  frozenEmbryoBatches: FrozenEmbryoBatch[];
  numSimulations: number;
}

export interface SimulationResult {
  completionRate: number;
  medianTimeToCompletionMonths: number | null;
  meanAgeAtCompletion: number | null;
  timeDistribution: number[];
  completionByMethod: Record<string, number>;
}

// Method codes
const NATURAL = 1;
const IVF_FRESH = 2;
const IVF_FROZEN_EGG = 3;
const IVF_FROZEN_EMBRYO = 4;

function drawIndividualFecundabilities(
  meanFecund: number,
  nCouples: number,
  rng: PRNG,
  cyclesTried: number,
): Float64Array {
  const alpha = Math.max(meanFecund * FECUNDABILITY_CONCENTRATION, 0.1);
  const beta = Math.max((1.0 - meanFecund) * FECUNDABILITY_CONCENTRATION + cyclesTried, 0.1);
  return rng.betaArray(alpha, beta, nCouples);
}

export function runSimulation(params: SimulationParams, seed = 42): SimulationResult {
  const N = params.numSimulations;
  const rng = new PRNG(seed);
  const bmiFr = bmiFecundabilityFr(params.bmi);
  const bmiIvf = bmiIvfAdjustment(params.bmi);
  const smokingFr = smokingFecundabilityFr(params.smokingStatus);
  const maxMonths = Math.floor((50 - params.femaleAge) * 12) + 1;

  // Handle case where desired family size is already met
  if (params.priorLiveBirths >= params.desiredChildren) {
    return {
      completionRate: 1.0,
      medianTimeToCompletionMonths: 0.0,
      meanAgeAtCompletion: params.femaleAge,
      timeDistribution: [1.0, ...new Array(11).fill(0)],
      completionByMethod: {
        natural: 1.0,
        ivf_fresh: 0.0,
        ivf_frozen_egg: 0.0,
        ivf_frozen_embryo: 0.0,
        incomplete: 0.0,
      },
    };
  }

  // Gravidity
  const hasPriorConceptions = params.priorLiveBirths > 0 || params.priorMiscarriages > 0;
  const useGravid = hasPriorConceptions;
  const hasMaleAge = params.maleAge !== null;

  // Frozen embryo batches (sorted youngest-first)
  const embryoBatchesSorted = [...params.frozenEmbryoBatches].sort(
    (a, b) => a.age_at_freeze - b.age_at_freeze,
  );
  const Be = embryoBatchesSorted.length;

  // Frozen egg batches (sorted youngest-first)
  const eggBatchesSorted = [...params.frozenEggBatches].sort(
    (a, b) => a.age_at_freeze - b.age_at_freeze,
  );
  const Bg = eggBatchesSorted.length;

  // Individual fecundability draws
  const initMeanFecund = fecundabilityCurve(params.femaleAge, useGravid);
  const individualFecund = drawIndividualFecundabilities(
    initMeanFecund, N, rng, params.cyclesTried,
  );
  const startingAgeMean = initMeanFecund;

  // Per-couple state
  const age = new Float64Array(N).fill(params.femaleAge);
  const maleAge = hasMaleAge ? new Float64Array(N).fill(params.maleAge!) : null;
  const childrenBorn = new Int32Array(N).fill(params.priorLiveBirths);
  const cyclesTried = new Int32Array(N).fill(params.cyclesTried);
  const active = new Uint8Array(N).fill(1);
  const waitingMonths = new Int32Array(N);
  const onIvf = new Uint8Array(N);
  const totalIvfCyclesUsed = new Int32Array(N);
  const ivfExhausted = new Uint8Array(N);
  const consecutiveMiscarriages = new Int32Array(N).fill(params.priorMiscarriages);

  // Frozen batch state per couple
  const embryoBatchRemaining = Be > 0
    ? Array.from({ length: N }, () => embryoBatchesSorted.map(b => b.num_embryos))
    : null;
  const eggBatchRemaining = Bg > 0
    ? Array.from({ length: N }, () => eggBatchesSorted.map(b => b.num_eggs))
    : null;

  const usingFrozenEmbryo = new Uint8Array(N);
  const usingFrozenEgg = new Uint8Array(N);
  const currentEmbryoBatchIdx = new Int32Array(N).fill(-1);
  const currentEggBatchIdx = new Int32Array(N).fill(-1);

  // Birth tracking
  const birthAges = Array.from({ length: N }, () => new Float64Array(params.desiredChildren).fill(NaN));
  const birthMethods = Array.from({ length: N }, () => new Int32Array(params.desiredChildren));

  for (let _cycle = 0; _cycle < maxMonths; _cycle++) {
    // Check if any active
    let anyActive = false;
    for (let i = 0; i < N; i++) {
      if (active[i]) { anyActive = true; break; }
    }
    if (!anyActive) break;

    // 1. Deactivate couples where age >= 50
    for (let i = 0; i < N; i++) {
      if (active[i] && age[i] >= 50.0) active[i] = 0;
    }

    // 2. Handle waiting couples
    for (let i = 0; i < N; i++) {
      if (active[i] && waitingMonths[i] > 0) {
        waitingMonths[i]--;
        age[i] += 1.0 / 12.0;
        if (maleAge) maleAge[i] += 1.0 / 12.0;
      }
    }

    // 3. Identify trying couples
    for (let i = 0; i < N; i++) {
      if (!active[i] || waitingMonths[i] > 0) continue;

      // Check eligibility for assisted reproduction
      const eligibleForAssisted =
        cyclesTried[i] >= params.cyclesBeforeIvf &&
        params.ivfWillingness !== "no" &&
        !onIvf[i] &&
        !ivfExhausted[i] &&
        !usingFrozenEmbryo[i] &&
        !usingFrozenEgg[i];

      if (eligibleForAssisted) {
        let assigned = false;
        // Priority 1: Frozen embryos
        if (!assigned && embryoBatchRemaining) {
          for (let bidx = 0; bidx < Be; bidx++) {
            if (currentEmbryoBatchIdx[i] === -1 && embryoBatchRemaining[i][bidx] > 0) {
              usingFrozenEmbryo[i] = 1;
              currentEmbryoBatchIdx[i] = bidx;
              assigned = true;
              break;
            }
          }
        }
        // Priority 2: Frozen eggs
        if (!assigned && eggBatchRemaining) {
          for (let bidx = 0; bidx < Bg; bidx++) {
            if (currentEggBatchIdx[i] === -1 && eggBatchRemaining[i][bidx] > 0) {
              usingFrozenEgg[i] = 1;
              currentEggBatchIdx[i] = bidx;
              assigned = true;
              break;
            }
          }
        }
        // Priority 3: Fresh IVF
        if (!assigned) {
          onIvf[i] = 1;
        }
      }

      // Compute conception probability
      let pConceive = 0;
      const isNatural = !onIvf[i] && !usingFrozenEmbryo[i] && !usingFrozenEgg[i];

      if (isNatural) {
        const currentMean = fecundabilityCurve(age[i], useGravid);
        const ageRatio = startingAgeMean > 0 ? currentMean / startingAgeMean : 0;
        pConceive = individualFecund[i] * ageRatio * bmiFr * smokingFr;
      } else if (onIvf[i]) {
        const lbr = ivfSuccessRate(age[i]) * bmiIvf;
        pConceive = lbr / (1.0 - ART_MISCARRIAGE_RATE);
      } else if (usingFrozenEmbryo[i]) {
        const bidx = currentEmbryoBatchIdx[i];
        const creationAge = embryoBatchesSorted[bidx].age_at_freeze;
        const pgtTested = embryoBatchesSorted[bidx].pgt_tested ?? false;
        const rate = pgtTested
          ? frozenEmbryoTransferRatePgt(creationAge)
          : frozenEmbryoTransferRate(creationAge);
        pConceive = (rate * bmiIvf) / (1.0 - ART_MISCARRIAGE_RATE);
        // Decrement embryo
        if (bidx >= 0 && embryoBatchRemaining![i][bidx] > 0) {
          embryoBatchRemaining![i][bidx]--;
        }
      } else if (usingFrozenEgg[i]) {
        const bidx = currentEggBatchIdx[i];
        const freezeAge = eggBatchesSorted[bidx].age_at_freeze;
        const remaining = eggBatchRemaining![i][bidx];
        const eggsThisCycle = Math.min(remaining, 9);
        const surviving = eggsThisCycle * OOCYTE_SURVIVAL_RATE;
        const perOocyte = frozenEggPerOocyteRate(freezeAge);
        const pFg = (1.0 - Math.pow(1.0 - perOocyte, surviving)) * bmiIvf;
        pConceive = pFg / (1.0 - ART_MISCARRIAGE_RATE);
        // Decrement eggs
        if (bidx >= 0) {
          eggBatchRemaining![i][bidx] = Math.max(0, remaining - eggsThisCycle);
        }
      }

      // Clip to [0, 1]
      pConceive = Math.max(0, Math.min(1, pConceive));

      // Random draw for conception
      const conceived = rng.random() < pConceive;

      if (conceived) {
        // Miscarriage check
        let pMiscarriage: number;
        const isArt = onIvf[i] || usingFrozenEmbryo[i] || usingFrozenEgg[i];
        if (isArt) {
          pMiscarriage = ART_MISCARRIAGE_RATE;
        } else {
          pMiscarriage = miscarriageCurve(age[i]);
          pMiscarriage = applyOddsRatio(pMiscarriage, recurrentMiscarriageOr(consecutiveMiscarriages[i]));
          if (maleAge) {
            pMiscarriage = applyOddsRatio(pMiscarriage, maleAgeMiscarriageOr(maleAge[i]));
          }
        }
        pMiscarriage = Math.max(0, Math.min(1, pMiscarriage));
        const miscarried = rng.random() < pMiscarriage;

        if (!miscarried) {
          // Live birth
          const birthIdx = childrenBorn[i];
          if (birthIdx < params.desiredChildren) {
            birthAges[i][birthIdx] = age[i];
            if (usingFrozenEmbryo[i]) {
              birthMethods[i][birthIdx] = IVF_FROZEN_EMBRYO;
            } else if (usingFrozenEgg[i]) {
              birthMethods[i][birthIdx] = IVF_FROZEN_EGG;
            } else if (onIvf[i]) {
              birthMethods[i][birthIdx] = IVF_FRESH;
            } else {
              birthMethods[i][birthIdx] = NATURAL;
            }
          }
          childrenBorn[i]++;
          waitingMonths[i] = params.minSpacingMonths;
          cyclesTried[i] = 0;
          onIvf[i] = 0;
          usingFrozenEmbryo[i] = 0;
          usingFrozenEgg[i] = 0;
          currentEmbryoBatchIdx[i] = -1;
          currentEggBatchIdx[i] = -1;
          totalIvfCyclesUsed[i] = 0;
          ivfExhausted[i] = 0;
          consecutiveMiscarriages[i] = 0;

          if (childrenBorn[i] >= params.desiredChildren) {
            active[i] = 0;
          }
        } else {
          // Miscarriage recovery
          waitingMonths[i] = 3;
          consecutiveMiscarriages[i]++;
          onIvf[i] = 0;
          usingFrozenEmbryo[i] = 0;
          usingFrozenEgg[i] = 0;
          currentEmbryoBatchIdx[i] = -1;
          currentEggBatchIdx[i] = -1;
        }
      } else {
        // No conception
        cyclesTried[i]++;

        // IVF cycle tracking
        if (onIvf[i]) {
          totalIvfCyclesUsed[i]++;
          if (totalIvfCyclesUsed[i] >= params.maxIvfCycles) {
            onIvf[i] = 0;
            ivfExhausted[i] = 1;
          }
        }

        // Frozen embryo exhaustion
        if (usingFrozenEmbryo[i] && embryoBatchRemaining) {
          const bidx = currentEmbryoBatchIdx[i];
          if (bidx >= 0 && embryoBatchRemaining[i][bidx] <= 0) {
            let foundNext = false;
            for (let nextBidx = bidx + 1; nextBidx < Be; nextBidx++) {
              if (embryoBatchRemaining[i][nextBidx] > 0) {
                currentEmbryoBatchIdx[i] = nextBidx;
                foundNext = true;
                break;
              }
            }
            if (!foundNext) {
              usingFrozenEmbryo[i] = 0;
              currentEmbryoBatchIdx[i] = -1;
            }
          }
        }

        // Frozen egg exhaustion
        if (usingFrozenEgg[i] && eggBatchRemaining) {
          const bidx = currentEggBatchIdx[i];
          if (bidx >= 0 && eggBatchRemaining[i][bidx] <= 0) {
            let foundNext = false;
            for (let nextBidx = bidx + 1; nextBidx < Bg; nextBidx++) {
              if (eggBatchRemaining[i][nextBidx] > 0) {
                currentEggBatchIdx[i] = nextBidx;
                foundNext = true;
                break;
              }
            }
            if (!foundNext) {
              usingFrozenEgg[i] = 0;
              currentEggBatchIdx[i] = -1;
            }
          }
        }
      }

      // Advance age
      if (onIvf[i] || usingFrozenEmbryo[i] || usingFrozenEgg[i]) {
        age[i] += 4.0 / 12.0;
        if (maleAge) maleAge[i] += 4.0 / 12.0;
      } else {
        age[i] += 1.0 / 12.0;
        if (maleAge) maleAge[i] += 1.0 / 12.0;
      }
    }
  }

  // --- Result compilation ---
  let completedCount = 0;
  const completionTimes: number[] = [];
  const completionAges: number[] = [];

  for (let i = 0; i < N; i++) {
    if (childrenBorn[i] >= params.desiredChildren) {
      completedCount++;
      const lastBirthAge = birthAges[i][params.desiredChildren - 1];
      const timeMonths = (lastBirthAge - params.femaleAge) * 12.0;
      completionTimes.push(timeMonths);
      completionAges.push(lastBirthAge);
    }
  }

  const completionRate = completedCount / N;

  let medianTime: number | null = null;
  let meanAge: number | null = null;
  if (completionTimes.length > 0) {
    completionTimes.sort((a, b) => a - b);
    const mid = Math.floor(completionTimes.length / 2);
    medianTime = completionTimes.length % 2 === 0
      ? (completionTimes[mid - 1] + completionTimes[mid]) / 2
      : completionTimes[mid];
    meanAge = completionAges.reduce((a, b) => a + b, 0) / completionAges.length;
  }

  // Time distribution histogram (12 bins)
  const timeDistribution = new Array(12).fill(0);
  if (completionTimes.length > 0) {
    const binWidth = maxMonths / 12;
    for (const t of completionTimes) {
      const bin = Math.min(Math.floor(t / binWidth), 11);
      timeDistribution[bin]++;
    }
    for (let i = 0; i < 12; i++) {
      timeDistribution[i] /= N;
    }
  }

  // Completion by method (hierarchy-based)
  let naturalCount = 0;
  let ivfFreshCount = 0;
  let ivfFrozenEggCount = 0;
  let ivfFrozenEmbryoCount = 0;

  for (let i = 0; i < N; i++) {
    if (childrenBorn[i] < params.desiredChildren) continue;
    const methods = birthMethods[i];
    let hasFrozenEmbryo = false;
    let hasFrozenEgg = false;
    let hasIvfFresh = false;
    let allNatural = true;

    for (let j = 0; j < params.desiredChildren; j++) {
      if (methods[j] === IVF_FROZEN_EMBRYO) hasFrozenEmbryo = true;
      if (methods[j] === IVF_FROZEN_EGG) hasFrozenEgg = true;
      if (methods[j] === IVF_FRESH) hasIvfFresh = true;
      if (methods[j] !== NATURAL && methods[j] !== 0) allNatural = false;
    }

    if (hasFrozenEmbryo) {
      ivfFrozenEmbryoCount++;
    } else if (hasFrozenEgg) {
      ivfFrozenEggCount++;
    } else if (hasIvfFresh) {
      ivfFreshCount++;
    } else if (allNatural) {
      naturalCount++;
    }
  }

  return {
    completionRate,
    medianTimeToCompletionMonths: medianTime,
    meanAgeAtCompletion: meanAge,
    timeDistribution,
    completionByMethod: {
      natural: naturalCount / N,
      ivf_fresh: ivfFreshCount / N,
      ivf_frozen_egg: ivfFrozenEggCount / N,
      ivf_frozen_embryo: ivfFrozenEmbryoCount / N,
      incomplete: 1.0 - completionRate,
    },
  };
}
