import type { SmokingStatus } from "../api/types";

/** Smoking fecundability reductions (approximate, for insight text) */
export const SMOKING_REDUCTIONS: Record<SmokingStatus, number> = {
  never: 0,
  former: 5,
  current_occasional: 12,
  current_regular: 20,
};

export const SMOKING_LABELS: Record<SmokingStatus, string> = {
  never: "Never smoked",
  former: "Former smoker",
  current_occasional: "Occasional smoker",
  current_regular: "Regular smoker",
};

/** BMI fecundability reductions (approximate, for insight text) */
export function getBmiReduction(bmi: number): number {
  if (bmi < 18.5) return 8;
  if (bmi < 25) return 0;
  if (bmi < 30) return 5;
  if (bmi < 35) return 10;
  if (bmi < 40) return 18;
  return 25;
}
