import { useState, useCallback } from "react";
import type { DraftFormState, FormState } from "./api/types";
import { validateDraft } from "./api/types";
import { INITIAL_DRAFT } from "./constants/defaults";
import { useSweep } from "./hooks/useSweep";
import { getTypicalEggsRetrieved } from "./constants/fertility";
import InputForm from "./components/form/InputForm";
import ResultsPanel from "./components/results/ResultsPanel";
import Footer from "./components/Footer";

interface WhatIfFreeze {
  enabled: boolean;
  numEggs: number;
}

function buildEffectiveForm(base: FormState, freeze: WhatIfFreeze): FormState {
  if (!freeze.enabled) return base;
  return {
    ...base,
    frozen_egg_batches: [
      ...base.frozen_egg_batches,
      { age_at_freeze: base.user_age, num_eggs: freeze.numEggs },
    ],
  };
}

export default function App() {
  const [form, setForm] = useState<DraftFormState>(INITIAL_DRAFT);
  const [submittedForm, setSubmittedForm] = useState<FormState | null>(null);
  const [whatIfFreeze, setWhatIfFreeze] = useState<WhatIfFreeze>({ enabled: false, numEggs: 15 });
  const { data, status, error, run } = useSweep();

  const handleChange = useCallback((updates: Partial<DraftFormState>) => {
    setForm((prev) => ({ ...prev, ...updates }));
  }, []);

  const handleSubmit = () => {
    const validated = validateDraft(form);
    if (!validated) return;
    setSubmittedForm(validated);
    setWhatIfFreeze({ enabled: false, numEggs: getTypicalEggsRetrieved(validated.user_age) });
    run(validated);
  };

  const handleWhatIfToggle = useCallback(
    (enabled: boolean) => {
      setWhatIfFreeze((prev) => {
        const numEggs = enabled && submittedForm
          ? getTypicalEggsRetrieved(submittedForm.user_age)
          : prev.numEggs;
        const next = { enabled, numEggs };
        if (submittedForm) run(buildEffectiveForm(submittedForm, next));
        return next;
      });
    },
    [submittedForm, run],
  );

  const handleWhatIfNumEggs = useCallback((numEggs: number) => {
    setWhatIfFreeze((prev) => ({ ...prev, numEggs }));
  }, []);

  const handleWhatIfApply = useCallback(() => {
    if (submittedForm) {
      setWhatIfFreeze((prev) => {
        run(buildEffectiveForm(submittedForm, prev));
        return prev;
      });
    }
  }, [submittedForm, run]);

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-stone-800">
          Fertility Forecaster
        </h1>
        <p className="mt-1 text-sm text-stone-500">
          Calculate your odds of getting pregnant at every age. See how timing,
          egg freezing, and IVF affect your chances of completing your family.
        </p>
      </header>

      <div className="grid gap-8 lg:grid-cols-[360px_1fr]">
        {/* Left panel: Form */}
        <div className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm h-fit">
          <InputForm
            form={form}
            onChange={handleChange}
            onSubmit={handleSubmit}
            loading={status === "loading"}
          />
        </div>

        {/* Right panel: Results */}
        <div className="min-w-0">
          {status === "loading" && !data && (
            <div className="flex items-center justify-center py-20 text-stone-400">
              <svg className="h-6 w-6 animate-spin mr-2" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Loading projections...
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              {error}
            </div>
          )}

          {data && submittedForm && (
            <ResultsPanel
              form={submittedForm}
              data={data}
              loading={status === "loading"}
              whatIfFreeze={whatIfFreeze}
              onWhatIfToggle={handleWhatIfToggle}
              onWhatIfNumEggs={handleWhatIfNumEggs}
              onWhatIfApply={handleWhatIfApply}
            />
          )}

          {!data && !error && status !== "loading" && (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="mb-4 rounded-full bg-stone-100 p-4">
                <svg className="h-8 w-8 text-stone-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
                </svg>
              </div>
              <p className="text-sm font-medium text-stone-600">
                Find out your chances of completing your family
              </p>
              <p className="mt-1 text-xs text-stone-400">
                Enter your age and family goals, then click "Calculate My Odds" to see your personalized fertility forecast
              </p>
            </div>
          )}
        </div>
      </div>

      <Footer />
    </div>
  );
}
