import { useCallback, useRef, useState } from "react";
import type { FormState, SweepRequest, SweepResponse } from "../api/types";
import { SWEEP_AGE_END, SWEEP_AGE_START, SWEEP_AGE_STEP } from "../constants/defaults";
import { computeSweep } from "../simulation/sweep";

type SweepStatus = "idle" | "loading" | "success" | "error";

interface UseSweepResult {
  data: SweepResponse | null;
  status: SweepStatus;
  error: string | null;
  run: (form: FormState, onSuccess?: () => void) => void;
}

function formToRequest(form: FormState): SweepRequest {
  const hasHistory = form.prior_live_births > 0 || form.prior_miscarriages > 0;
  const sweepStart = hasHistory ? Math.max(SWEEP_AGE_START, form.user_age) : SWEEP_AGE_START;
  return {
    age_range_start: sweepStart,
    age_range_end: SWEEP_AGE_END,
    age_step: SWEEP_AGE_STEP,
    desired_children: form.desired_children,
    male_age_offset: form.male_age_offset,
    bmi: form.bmi,
    acceptable_probability: form.acceptable_probability,
    ivf_willingness: form.ivf_willingness,
    min_spacing_months: form.min_spacing_months,
    prior_live_births: form.prior_live_births,
    prior_miscarriages: form.prior_miscarriages,
    cycles_tried: form.cycles_tried,
    cycles_before_ivf: form.cycles_before_ivf,
    max_ivf_cycles: form.max_ivf_cycles,
    smoking_status: form.smoking_status,
    frozen_egg_batches: form.frozen_egg_batches,
    frozen_embryo_batches: form.frozen_embryo_batches,
    age_at_last_birth: form.age_at_last_birth,
    age_at_last_miscarriage: form.age_at_last_miscarriage,
  };
}

export function useSweep(): UseSweepResult {
  const [data, setData] = useState<SweepResponse | null>(null);
  const [status, setStatus] = useState<SweepStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const runIdRef = useRef(0);

  const run = useCallback((form: FormState, onSuccess?: () => void) => {
    const runId = ++runIdRef.current;

    setStatus("loading");
    setError(null);

    // Run in a microtask to allow the UI to show the loading state
    setTimeout(() => {
      try {
        const response = computeSweep(formToRequest(form));
        if (runId !== runIdRef.current) return; // stale
        setData(response);
        setStatus("success");
        onSuccess?.();
      } catch (err: unknown) {
        if (runId !== runIdRef.current) return;
        setError(err instanceof Error ? err.message : "Unknown error");
        setStatus("error");
      }
    }, 0);
  }, []);

  return { data, status, error, run };
}
