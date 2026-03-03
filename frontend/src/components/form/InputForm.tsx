import type { DraftFormState, IvfWillingness } from "../../api/types";
import CollapsibleSection from "./CollapsibleSection";
import HealthLifestyle from "./HealthLifestyle";
import FrozenStorage from "./FrozenStorage";
import AdvancedParams from "./AdvancedParams";
import { inputClass, inlineSelectClass } from "./styles";
import { SWEEP_AGE_START, SWEEP_AGE_END, DEFAULT_FALLBACK_AGE } from "../../constants/defaults";

interface Props {
  form: DraftFormState;
  onChange: (updates: Partial<DraftFormState>) => void;
  onSubmit: () => void;
  loading: boolean;
}

function PillToggle({
  value,
  onChange,
  label,
}: {
  value: boolean;
  onChange: (v: boolean) => void;
  label: [string, string];
}) {
  return (
    <div className="inline-flex rounded-md border border-stone-300 text-sm">
      <button
        type="button"
        onClick={() => onChange(false)}
        className={`px-3 py-1.5 rounded-l-md transition-colors ${
          !value
            ? "bg-stone-800 text-white"
            : "bg-white text-stone-600 hover:bg-stone-50"
        }`}
      >
        {label[0]}
      </button>
      <button
        type="button"
        onClick={() => onChange(true)}
        className={`px-3 py-1.5 rounded-r-md transition-colors ${
          value
            ? "bg-stone-800 text-white"
            : "bg-white text-stone-600 hover:bg-stone-50"
        }`}
      >
        {label[1]}
      </button>
    </div>
  );
}

export default function InputForm({ form, onChange, onSubmit, loading }: Props) {
  const ageError =
    form.user_age !== null && (form.user_age < SWEEP_AGE_START || form.user_age > SWEEP_AGE_END)
      ? `Please enter an age between ${SWEEP_AGE_START} and ${SWEEP_AGE_END}`
      : null;
  const canSubmit =
    form.user_age !== null &&
    !ageError &&
    form.desired_children !== null;
  const userAge = form.user_age ?? DEFAULT_FALLBACK_AGE;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (canSubmit) onSubmit();
      }}
      className="space-y-6"
    >
      {/* Q1: Age */}
      <div>
        <label className="mb-1 block text-sm font-semibold text-stone-700">
          How old are you? (Mother's age)
        </label>
        <input
          type="number"
          min={SWEEP_AGE_START}
          max={SWEEP_AGE_END}
          value={form.user_age ?? ""}
          placeholder="Your age"
          onFocus={(e) => e.target.select()}
          onChange={(e) =>
            onChange({
              user_age: e.target.value ? +e.target.value : null,
            })
          }
          className={`${inputClass} ${ageError ? "border-red-400 focus:border-red-500 focus:ring-red-500" : ""}`}
        />
        {ageError && (
          <p className="mt-1 text-xs text-red-600">{ageError}</p>
        )}
      </div>

      {/* Q2: Confidence sentence */}
      <div>
        <label className="mb-2 block text-sm font-semibold text-stone-700">
          What's your family goal?
        </label>
        <p className="text-sm text-stone-600 leading-relaxed">
          I want to be at least{" "}
          <select
            value={form.acceptable_probability}
            onChange={(e) =>
              onChange({ acceptable_probability: +e.target.value })
            }
            className={inlineSelectClass}
          >
            <option value={0.5}>50%</option>
            <option value={0.75}>75%</option>
            <option value={0.8}>80%</option>
            <option value={0.9}>90%</option>
            <option value={0.95}>95%</option>
            <option value={0.99}>99%</option>
          </select>{" "}
          confident that I have at least{" "}
          <select
            value={form.desired_children ?? ""}
            onChange={(e) =>
              onChange({
                desired_children: e.target.value ? +e.target.value : null,
              })
            }
            className={inlineSelectClass}
          >
            <option value="" disabled>#</option>
            <option value={1}>1</option>
            <option value={2}>2</option>
            <option value={3}>3</option>
            <option value={4}>4</option>
            <option value={5}>5</option>
            <option value={6}>6</option>
          </select>{" "}
          {form.desired_children === 1 ? "child" : "children"}
        </p>

      </div>

      {/* Q3: IVF willingness */}
      <div>
        <label className="mb-1 block text-sm font-semibold text-stone-700">
          Open to IVF?
        </label>
        <select
          value={form.ivf_willingness}
          onChange={(e) =>
            onChange({ ivf_willingness: e.target.value as IvfWillingness })
          }
          className={inputClass}
        >
          <option value="no">No</option>
          <option value="last_resort">Yes, as a last resort</option>
        </select>
      </div>

      {/* Q4: Started trying */}
      <div>
        <label className="mb-2 block text-sm font-semibold text-stone-700">
          Have you started trying to have kids yet?
        </label>
        <PillToggle
          value={form.has_started_trying}
          onChange={(v) => onChange({ has_started_trying: v })}
          label={["No", "Yes"]}
        />

        {form.has_started_trying && (
          <div className="mt-3 space-y-3 rounded-md bg-stone-50 p-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-stone-500">
                Prior live births
              </label>
              <input
                type="number"
                min={0}
                max={10}
                value={form.prior_live_births || ""}
                onFocus={(e) => e.target.select()}
                onChange={(e) =>
                  onChange({
                    prior_live_births: e.target.value
                      ? Math.max(0, +e.target.value)
                      : 0,
                  })
                }
                placeholder="0"
                className={inputClass}
              />
            </div>

            {form.prior_live_births > 0 && (
              <div>
                <label className="mb-1 block text-xs font-medium text-stone-500">
                  Age at last birth
                </label>
                <input
                  type="number"
                  min={18}
                  max={userAge}
                  value={form.age_at_last_birth ?? ""}
                  onFocus={(e) => e.target.select()}
                  onChange={(e) =>
                    onChange({
                      age_at_last_birth: e.target.value
                        ? +e.target.value
                        : null,
                    })
                  }
                  placeholder="Optional"
                  className={inputClass}
                />
              </div>
            )}

            <div>
              <label className="mb-1 block text-xs font-medium text-stone-500">
                Prior miscarriages
              </label>
              <input
                type="number"
                min={0}
                max={10}
                value={form.prior_miscarriages || ""}
                onFocus={(e) => e.target.select()}
                onChange={(e) =>
                  onChange({
                    prior_miscarriages: e.target.value
                      ? Math.max(0, +e.target.value)
                      : 0,
                  })
                }
                placeholder="0"
                className={inputClass}
              />
            </div>

            {form.prior_miscarriages > 0 && (
              <div>
                <label className="mb-1 block text-xs font-medium text-stone-500">
                  Age at last miscarriage
                </label>
                <input
                  type="number"
                  min={18}
                  max={userAge}
                  value={form.age_at_last_miscarriage ?? ""}
                  onFocus={(e) => e.target.select()}
                  onChange={(e) =>
                    onChange({
                      age_at_last_miscarriage: e.target.value
                        ? +e.target.value
                        : null,
                    })
                  }
                  placeholder="Optional"
                  className={inputClass}
                />
              </div>
            )}

            <div>
              <label className="mb-1 block text-xs font-medium text-stone-500">
                Cycles tried without conception
              </label>
              <input
                type="number"
                min={0}
                max={60}
                value={form.cycles_tried || ""}
                onFocus={(e) => e.target.select()}
                onChange={(e) =>
                  onChange({
                    cycles_tried: e.target.value
                      ? Math.max(0, +e.target.value)
                      : 0,
                  })
                }
                placeholder="0"
                className={inputClass}
              />
            </div>
          </div>
        )}
      </div>

      {/* Q5: Frozen reserves */}
      <div>
        <label className="mb-2 block text-sm font-semibold text-stone-700">
          Do you have frozen eggs or embryos?
        </label>
        <PillToggle
          value={form.has_frozen_reserves}
          onChange={(v) => onChange({ has_frozen_reserves: v })}
          label={["No", "Yes"]}
        />

        {form.has_frozen_reserves && (
          <div className="mt-3 rounded-md bg-stone-50 p-3">
            <FrozenStorage form={form} onChange={onChange} />
          </div>
        )}
      </div>

      {/* Optional collapsible sections */}
      <div className="border-t border-stone-200 pt-2">
        <CollapsibleSection title="Health & Lifestyle">
          <HealthLifestyle form={form} onChange={onChange} />
        </CollapsibleSection>

        <CollapsibleSection title="Advanced">
          <AdvancedParams form={form} onChange={onChange} />
        </CollapsibleSection>
      </div>

      {/* Submit */}
      <div>
        <button
          type="submit"
          disabled={loading || !canSubmit}
          className="w-full rounded-md bg-stone-800 px-4 py-3 text-sm font-semibold text-white hover:bg-stone-900 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg
                className="h-4 w-4 animate-spin"
                viewBox="0 0 24 24"
                fill="none"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
              Calculating...
            </span>
          ) : (
            "Calculate My Odds"
          )}
        </button>
        {!canSubmit && (
          <p className="mt-2 text-center text-xs text-stone-400">
            Enter your age and number of children to continue
          </p>
        )}
      </div>
    </form>
  );
}
