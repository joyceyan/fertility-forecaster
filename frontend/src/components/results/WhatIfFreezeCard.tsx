interface Props {
  age: number;
  enabled: boolean;
  numEggs: number;
  onToggle: (enabled: boolean) => void;
  onNumEggsChange: (numEggs: number) => void;
  onApply: () => void;
}

export default function WhatIfFreezeCard({
  age,
  enabled,
  numEggs,
  onToggle,
  onNumEggsChange,
  onApply,
}: Props) {
  return (
    <div className="rounded-lg border border-stone-200 bg-stone-50 p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h4 className="text-sm font-semibold text-stone-700">
            What if I freeze eggs at {age}?
          </h4>
          <p className="mt-0.5 text-xs text-stone-500">
            See how freezing eggs now could improve your future odds
          </p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={enabled}
          onClick={() => onToggle(!enabled)}
          className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[#6b9e8a] ${
            enabled ? "bg-[#6b9e8a]" : "bg-stone-300"
          }`}
        >
          <span
            className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow ring-0 transition-transform duration-200 ${
              enabled ? "translate-x-5" : "translate-x-0"
            }`}
          />
        </button>
      </div>

      {enabled && (
        <div className="mt-3 flex items-center gap-2">
          <label htmlFor="whatif-num-eggs" className="text-xs text-stone-600">
            Number of eggs to freeze:
          </label>
          <input
            id="whatif-num-eggs"
            type="number"
            min={1}
            max={40}
            value={numEggs}
            onChange={(e) => {
              const v = parseInt(e.target.value, 10);
              if (!isNaN(v) && v >= 1 && v <= 40) onNumEggsChange(v);
            }}
            className="w-16 rounded border border-stone-300 bg-white px-2 py-1 text-sm text-stone-700 focus:border-[#6b9e8a] focus:outline-none focus:ring-1 focus:ring-[#6b9e8a]"
          />
          <button
            type="button"
            onClick={onApply}
            className="rounded bg-[#6b9e8a] px-3 py-1 text-xs font-medium text-white transition-colors hover:bg-[#5a8d79] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[#6b9e8a]"
          >
            Update
          </button>
        </div>
      )}
    </div>
  );
}
