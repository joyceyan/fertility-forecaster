export interface FrozenEggBatch {
  age_at_freeze: number;
  num_eggs: number;
}

export interface FrozenEmbryoBatch {
  age_at_freeze: number;
  num_embryos: number;
  pgt_tested?: boolean;
}

export type IvfWillingness = "yes" | "no" | "last_resort";
export type SmokingStatus =
  | "never"
  | "former"
  | "current_occasional"
  | "current_regular";

export interface SweepRequest {
  age_range_start: number;
  age_range_end: number;
  age_step?: number;
  desired_children: number;
  male_age_offset?: number | null;
  bmi?: number | null;
  acceptable_probability?: number;
  ivf_willingness: IvfWillingness;
  min_spacing_months?: number;
  prior_live_births?: number;
  prior_miscarriages?: number;
  cycles_tried?: number;
  cycles_before_ivf?: number;
  max_ivf_cycles?: number;
  smoking_status?: SmokingStatus;
  frozen_egg_batches?: FrozenEggBatch[];
  frozen_embryo_batches?: FrozenEmbryoBatch[];
  age_at_last_birth?: number | null;
  age_at_last_miscarriage?: number | null;
}

export interface SweepPoint {
  starting_age: number;
  completion_rate: number;
  completion_by_method: Record<string, number>;
  median_time_months: number | null;
}

export interface SweepScenarios {
  natural_only: SweepPoint[];
  with_ivf: SweepPoint[];
  with_frozen: SweepPoint[] | null;
}

export interface SweepResponse {
  results: SweepPoint[];
  scenarios: SweepScenarios;
}

/** Form state used in the UI (includes user_age which is separate from sweep range) */
export interface FormState {
  user_age: number;
  desired_children: number;
  ivf_willingness: IvfWillingness;
  min_spacing_months: number;
  bmi: number | null;
  smoking_status: SmokingStatus;
  prior_live_births: number;
  prior_miscarriages: number;
  cycles_tried: number;
  male_age_offset: number | null;
  frozen_egg_batches: FrozenEggBatch[];
  frozen_embryo_batches: FrozenEmbryoBatch[];
  max_ivf_cycles: number;
  cycles_before_ivf: number;
  acceptable_probability: number;
  age_at_last_birth: number | null;
  age_at_last_miscarriage: number | null;
}

/** Draft form state — required fields are nullable until the user fills them in */
export interface DraftFormState {
  user_age: number | null;
  desired_children: number | null;
  acceptable_probability: number;
  ivf_willingness: IvfWillingness;
  min_spacing_months: number;
  has_started_trying: boolean;
  has_frozen_reserves: boolean;
  bmi: number | null;
  smoking_status: SmokingStatus;
  prior_live_births: number;
  prior_miscarriages: number;
  cycles_tried: number;
  male_age_offset: number | null;
  frozen_egg_batches: FrozenEggBatch[];
  frozen_embryo_batches: FrozenEmbryoBatch[];
  max_ivf_cycles: number;
  cycles_before_ivf: number;
  age_at_last_birth: number | null;
  age_at_last_miscarriage: number | null;
}

/** Validates a draft and returns a FormState if required fields are filled, null otherwise */
export function validateDraft(draft: DraftFormState): FormState | null {
  if (draft.user_age === null || draft.desired_children === null) return null;

  return {
    user_age: draft.user_age,
    desired_children: draft.desired_children,
    acceptable_probability: draft.acceptable_probability,
    ivf_willingness: draft.ivf_willingness,
    min_spacing_months: draft.min_spacing_months,
    bmi: draft.bmi,
    smoking_status: draft.smoking_status,
    prior_live_births: draft.has_started_trying ? draft.prior_live_births : 0,
    prior_miscarriages: draft.has_started_trying ? draft.prior_miscarriages : 0,
    cycles_tried: draft.has_started_trying ? draft.cycles_tried : 0,
    age_at_last_birth: draft.has_started_trying ? draft.age_at_last_birth : null,
    age_at_last_miscarriage: draft.has_started_trying ? draft.age_at_last_miscarriage : null,
    male_age_offset: draft.male_age_offset,
    frozen_egg_batches: draft.has_frozen_reserves ? draft.frozen_egg_batches : [],
    frozen_embryo_batches: draft.has_frozen_reserves ? draft.frozen_embryo_batches : [],
    max_ivf_cycles: draft.max_ivf_cycles,
    cycles_before_ivf: draft.cycles_before_ivf,
  };
}
