import { useState } from "react";
import type { DraftFormState } from "../../api/types";
import { inputClass } from "./styles";
import { DEFAULT_FALLBACK_AGE } from "../../constants/defaults";

interface Props {
  form: DraftFormState;
  onChange: (updates: Partial<DraftFormState>) => void;
}

const SPACING_STOPS = [6, 9, 12, 15, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72];

function spacingLabel(months: number): string {
  if (months < 18) return `${months} months`;
  if (months % 12 === 0) return `${months / 12} ${months === 12 ? "year" : "years"}`;
  return `${(months / 12).toFixed(1)} years`;
}

function snapToStop(index: number): number {
  return SPACING_STOPS[Math.max(0, Math.min(index, SPACING_STOPS.length - 1))]!;
}

function stopIndex(months: number): number {
  let closest = 0;
  for (let i = 1; i < SPACING_STOPS.length; i++) {
    if (Math.abs(SPACING_STOPS[i]! - months) < Math.abs(SPACING_STOPS[closest]! - months)) {
      closest = i;
    }
  }
  return closest;
}

export default function AdvancedParams({ form, onChange }: Props) {
  const [showFatherInfo, setShowFatherInfo] = useState(false);
  const userAge = form.user_age ?? DEFAULT_FALLBACK_AGE;
  const maleAge =
    form.male_age_offset !== null ? userAge + form.male_age_offset : null;

  return (
    <div className="space-y-4">
      <div>
        <div className="mb-1 flex items-center gap-1">
          <label className="text-sm font-medium text-stone-600">
            Father's age
          </label>
          <button
            type="button"
            onClick={() => setShowFatherInfo(!showFatherInfo)}
            className="text-stone-400 hover:text-stone-600"
            aria-label="More info about father's age"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </button>
        </div>
        {showFatherInfo && (
          <p className="mb-2 text-xs leading-relaxed text-stone-500 bg-stone-50 rounded-md p-2">
            It only matters when the father is over 40, where it may modestly increase miscarriage risk.
          </p>
        )}
        <input
          type="number"
          min={18}
          max={70}
          value={maleAge ?? ""}
          onChange={(e) =>
            onChange({
              male_age_offset: e.target.value
                ? +e.target.value - userAge
                : null,
            })
          }
          placeholder="Optional"
          className={inputClass}
        />
        {maleAge !== null && maleAge >= 40 && (
          <p className="mt-1 text-xs text-amber-600">
            Partner age 40+ may affect time to conception and miscarriage risk.
          </p>
        )}
      </div>

      {form.desired_children !== null && form.desired_children > 1 && (
        <div>
          <label className="mb-1 block text-sm font-medium text-stone-600">
            How long do you want to wait after giving birth before trying to conceive again?
          </label>
          <input
            type="range"
            min={0}
            max={SPACING_STOPS.length - 1}
            step={1}
            value={stopIndex(form.min_spacing_months)}
            onChange={(e) =>
              onChange({ min_spacing_months: snapToStop(+e.target.value) })
            }
            className="w-full accent-stone-600"
          />
          <div className="text-xs text-stone-500 text-right">
            {spacingLabel(form.min_spacing_months)}
          </div>
        </div>
      )}

      {form.ivf_willingness !== "no" && (
        <>
          <div>
            <label className="mb-1 block text-sm font-medium text-stone-600">
              Max IVF cycles per child
            </label>
            <input
              type="number"
              min={1}
              max={10}
              value={form.max_ivf_cycles || ""}
              onFocus={(e) => e.target.select()}
              onChange={(e) =>
                onChange({ max_ivf_cycles: e.target.value ? Math.max(1, Math.min(10, +e.target.value)) : 1 })
              }
              className={inputClass}
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-stone-600">
              Natural cycles before trying IVF
            </label>
            <input
              type="number"
              min={0}
              max={36}
              value={form.cycles_before_ivf || ""}
              onFocus={(e) => e.target.select()}
              onChange={(e) =>
                onChange({ cycles_before_ivf: e.target.value ? Math.max(0, Math.min(36, +e.target.value)) : 0 })
              }
              className={inputClass}
            />
          </div>
        </>
      )}
    </div>
  );
}
