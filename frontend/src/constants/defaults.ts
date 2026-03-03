import type { DraftFormState } from "../api/types";

export const INITIAL_DRAFT: DraftFormState = {
  user_age: null,
  desired_children: null,
  acceptable_probability: 0.9,
  ivf_willingness: "last_resort",
  min_spacing_months: 15,
  has_started_trying: false,
  has_frozen_reserves: false,
  bmi: null,
  smoking_status: "never",
  prior_live_births: 0,
  prior_miscarriages: 0,
  cycles_tried: 0,
  male_age_offset: null,
  frozen_egg_batches: [],
  frozen_embryo_batches: [],
  max_ivf_cycles: 3,
  cycles_before_ivf: 12,
  age_at_last_birth: null,
  age_at_last_miscarriage: null,
};

export const SWEEP_AGE_START = 18;
export const SWEEP_AGE_END = 45;
export const SWEEP_AGE_STEP = 1;

/** Fallback age used when user_age is null (for non-critical defaults like frozen batch age) */
export const DEFAULT_FALLBACK_AGE = 30;
