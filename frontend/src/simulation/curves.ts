/**
 * Age-dependent fertility curves and adjustment factors.
 * Age-dependent fertility curves and adjustment factors used by the simulation.
 */

import type { SmokingStatus } from "../api/types";

// Wesselink et al. 2017 Table 3 fecundity ratios at age bracket midpoints.
const FECUNDABILITY_AGES = [21, 26, 29, 32, 35, 38, 42.5, 50];
const FECUNDABILITY_FR_NULLIGRAVID = [1.0, 0.88, 0.8, 0.84, 0.68, 0.51, 0.2, 0.0];
const FECUNDABILITY_FR_GRAVID = [1.0, 0.92, 0.95, 0.88, 0.96, 0.7, 0.48, 0.0];

export const BASE_FECUNDABILITY = 0.23;

// Magnus et al. 2019 miscarriage rates, flattened below age 25.
const MISCARRIAGE_AGES = [18.0, 27.0, 32.0, 37.0, 42.0, 47.5];
const MISCARRIAGE_RATES = [0.098, 0.098, 0.108, 0.167, 0.322, 0.536];

export const OOCYTE_SURVIVAL_RATE = 0.785;
export const ART_MISCARRIAGE_RATE = 0.15;
export const FECUNDABILITY_CONCENTRATION = 4.23;

/** Linear interpolation matching numpy.interp behavior. */
function interp(x: number, xp: number[], fp: number[]): number {
  if (x <= xp[0]) return fp[0];
  if (x >= xp[xp.length - 1]) return fp[fp.length - 1];
  for (let i = 1; i < xp.length; i++) {
    if (x <= xp[i]) {
      const t = (x - xp[i - 1]) / (xp[i] - xp[i - 1]);
      return fp[i - 1] + t * (fp[i] - fp[i - 1]);
    }
  }
  return fp[fp.length - 1];
}

/** Monthly probability of conception by female age (natural intercourse). */
export function fecundabilityCurve(age: number, gravid: boolean): number {
  const fr = gravid
    ? interp(age, FECUNDABILITY_AGES, FECUNDABILITY_FR_GRAVID)
    : interp(age, FECUNDABILITY_AGES, FECUNDABILITY_FR_NULLIGRAVID);
  return fr * BASE_FECUNDABILITY;
}

/** Probability of miscarriage given clinical pregnancy, by female age. */
export function miscarriageCurve(age: number): number {
  return interp(age, MISCARRIAGE_AGES, MISCARRIAGE_RATES);
}

/** Apply an odds ratio to a base probability. */
export function applyOddsRatio(baseProb: number, oddsRatio: number): number {
  return (baseProb * oddsRatio) / (1.0 - baseProb + baseProb * oddsRatio);
}

/** Odds ratio for recurrent miscarriage based on consecutive count. */
export function recurrentMiscarriageOr(consecutiveMiscarriages: number): number {
  if (consecutiveMiscarriages === 0) return 1.0;
  if (consecutiveMiscarriages === 1) return 1.54;
  if (consecutiveMiscarriages === 2) return 2.21;
  return 3.97;
}

/** Odds ratio for miscarriage based on male age. */
export function maleAgeMiscarriageOr(maleAge: number): number {
  if (maleAge >= 45) return 1.43;
  if (maleAge >= 40) return 1.23;
  if (maleAge >= 35) return 1.15;
  return 1.0;
}

/** Per-transfer live birth rate for fresh IVF by female age (SART 2023). */
export function ivfSuccessRate(age: number): number {
  if (age < 35) return 0.405;
  if (age < 38) return 0.317;
  if (age < 41) return 0.213;
  if (age < 43) return 0.11;
  if (age < 45) return 0.04;
  return 0.01;
}

/** Per-oocyte live birth rate for frozen eggs by age at retrieval (Namath 2025). */
export function frozenEggPerOocyteRate(retrievalAge: number): number {
  if (retrievalAge < 35) return 0.13;
  if (retrievalAge < 38) return 0.09;
  if (retrievalAge < 41) return 0.06;
  return 0.04;
}

/** Per-transfer LBR for frozen embryo transfer, non-PGT-A (SART 2023). */
export function frozenEmbryoTransferRate(creationAge: number): number {
  if (creationAge < 35) return 0.405;
  if (creationAge < 38) return 0.317;
  if (creationAge < 41) return 0.213;
  if (creationAge < 43) return 0.11;
  return 0.036;
}

/** Per-transfer LBR for PGT-A tested frozen embryos (SART 2023). */
export function frozenEmbryoTransferRatePgt(creationAge: number): number {
  if (creationAge < 35) return 0.545;
  if (creationAge < 38) return 0.532;
  if (creationAge < 41) return 0.514;
  if (creationAge < 43) return 0.499;
  return 0.463;
}

/** Fecundability ratio based on BMI (McKinnon 2016). */
export function bmiFecundabilityFr(bmi: number | null): number {
  if (bmi === null) return 1.0;
  if (bmi < 18.5) return 1.05;
  if (bmi < 25) return 1.0;
  if (bmi < 30) return 1.01;
  if (bmi < 35) return 0.98;
  if (bmi < 40) return 0.78;
  if (bmi < 45) return 0.61;
  return 0.42;
}

/** IVF success adjustment for BMI. */
export function bmiIvfAdjustment(bmi: number | null): number {
  if (bmi === null || bmi < 30) return 1.0;
  return 0.85;
}

/** Fecundability ratio based on smoking status. */
export function smokingFecundabilityFr(status: SmokingStatus): number {
  switch (status) {
    case "never": return 1.0;
    case "former": return 0.89;
    case "current_occasional": return 0.88;
    case "current_regular": return 0.77;
  }
}
