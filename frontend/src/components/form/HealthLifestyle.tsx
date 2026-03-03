import { useState } from "react";
import type { DraftFormState, SmokingStatus } from "../../api/types";
import { SMOKING_LABELS } from "../../constants/fertility";
import BmiCalculator from "./BmiCalculator";
import { inputClass } from "./styles";

interface Props {
  form: DraftFormState;
  onChange: (updates: Partial<DraftFormState>) => void;
}

export default function HealthLifestyle({ form, onChange }: Props) {
  const [showCalc, setShowCalc] = useState(false);

  return (
    <div className="space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-stone-600">
          BMI {form.bmi !== null && <span className="text-stone-400">({form.bmi})</span>}
        </label>
        <div className="flex gap-2">
          <input
            type="number"
            min={15}
            max={60}
            step={0.1}
            value={form.bmi ?? ""}
            onChange={(e) =>
              onChange({ bmi: e.target.value ? +e.target.value : null })
            }
            placeholder="Optional"
            className={`${inputClass} !w-auto flex-1`}
          />
          <button
            type="button"
            onClick={() => setShowCalc(!showCalc)}
            className="rounded-md border border-stone-300 px-3 py-2 text-xs text-stone-600 hover:bg-stone-100"
          >
            {showCalc ? "Hide" : "Calculate"}
          </button>
        </div>
        {showCalc && (
          <div className="mt-2">
            <BmiCalculator onApply={(bmi) => { onChange({ bmi }); setShowCalc(false); }} />
          </div>
        )}
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-stone-600">
          Smoking status
        </label>
        <select
          value={form.smoking_status}
          onChange={(e) =>
            onChange({ smoking_status: e.target.value as SmokingStatus })
          }
          className={inputClass}
        >
          {Object.entries(SMOKING_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
