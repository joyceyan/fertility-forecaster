import { useBmiCalculator } from "../../hooks/useBmiCalculator";

interface Props {
  onApply: (bmi: number) => void;
}

export default function BmiCalculator({ onApply }: Props) {
  const calc = useBmiCalculator();

  return (
    <div className="rounded-md border border-stone-200 bg-stone-50 p-3 space-y-3">
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => calc.setUnit("imperial")}
          className={`rounded px-2 py-1 text-xs font-medium ${
            calc.unit === "imperial"
              ? "bg-stone-700 text-white"
              : "bg-stone-200 text-stone-600"
          }`}
        >
          Imperial
        </button>
        <button
          type="button"
          onClick={() => calc.setUnit("metric")}
          className={`rounded px-2 py-1 text-xs font-medium ${
            calc.unit === "metric"
              ? "bg-stone-700 text-white"
              : "bg-stone-200 text-stone-600"
          }`}
        >
          Metric
        </button>
      </div>

      {calc.unit === "imperial" ? (
        <div className="grid grid-cols-3 gap-2">
          <div>
            <label className="block text-xs text-stone-500">Feet</label>
            <input
              type="number"
              min={3}
              max={7}
              value={calc.heightFeet}
              onChange={(e) => calc.setHeightFeet(+e.target.value)}
              className="w-full rounded border border-stone-300 px-2 py-1 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-stone-500">Inches</label>
            <input
              type="number"
              min={0}
              max={11}
              value={calc.heightInches}
              onChange={(e) => calc.setHeightInches(+e.target.value)}
              className="w-full rounded border border-stone-300 px-2 py-1 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-stone-500">Weight (lbs)</label>
            <input
              type="number"
              min={50}
              max={500}
              value={calc.weightLbs}
              onChange={(e) => calc.setWeightLbs(+e.target.value)}
              className="w-full rounded border border-stone-300 px-2 py-1 text-sm"
            />
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs text-stone-500">Height (cm)</label>
            <input
              type="number"
              min={100}
              max={250}
              value={calc.heightCm}
              onChange={(e) => calc.setHeightCm(+e.target.value)}
              className="w-full rounded border border-stone-300 px-2 py-1 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-stone-500">Weight (kg)</label>
            <input
              type="number"
              min={30}
              max={250}
              value={calc.weightKg}
              onChange={(e) => calc.setWeightKg(+e.target.value)}
              className="w-full rounded border border-stone-300 px-2 py-1 text-sm"
            />
          </div>
        </div>
      )}

      {calc.bmi !== null && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-stone-600">
            Calculated BMI: <strong>{calc.bmi}</strong>
          </span>
          <button
            type="button"
            onClick={() => calc.bmi !== null && onApply(calc.bmi)}
            className="rounded bg-stone-600 px-3 py-1 text-xs font-medium text-white hover:bg-stone-700"
          >
            Use this BMI
          </button>
        </div>
      )}
    </div>
  );
}
