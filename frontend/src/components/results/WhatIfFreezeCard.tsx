import { getTypicalEggsRetrieved } from "../../constants/fertility";

interface Props {
  age: number;
  enabled: boolean;
  numEggs: number;
  onToggle: (enabled: boolean) => void;
  onNumEggsChange: (numEggs: number) => void;
  onApply: () => void;
}

/** Per-oocyte live birth rate by age at freeze (Namath et al. 2025). */
function getPerOocyteRate(age: number): number {
  if (age < 35) return 0.13;
  if (age < 38) return 0.09;
  if (age < 41) return 0.06;
  return 0.04;
}

/** Approximate typical range of eggs retrieved per cycle, by age. */
function getEggRange(age: number): [number, number] {
  if (age < 30) return [8, 25];
  if (age < 35) return [6, 20];
  if (age < 38) return [4, 16];
  if (age < 41) return [3, 12];
  if (age < 43) return [1, 8];
  return [1, 5];
}

/** Approximate eggs needed for ~93% chance of at least one live birth (Namath et al. 2025). */
function getEggsFor93Pct(age: number): number {
  if (age < 35) return 15;
  if (age < 38) return 20;
  if (age < 41) return 30;
  return 45;
}

export default function WhatIfFreezeCard({
  age,
  enabled,
  numEggs,
  onToggle,
  onNumEggsChange,
  onApply,
}: Props) {
  const typical = getTypicalEggsRetrieved(age);
  const [rangeLow, rangeHigh] = getEggRange(age);
  const perOocyte = getPerOocyteRate(age);
  const eggsFor93 = getEggsFor93Pct(age);

  return (
    <div className={`rounded-lg border border-stone-200 p-4 ${enabled ? "bg-white" : "bg-stone-50"}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h4 className="text-sm font-semibold text-stone-700">
            What if I freeze eggs at {age}?
          </h4>
          {!enabled && (
            <p className="mt-0.5 text-xs text-stone-500">
              See how freezing eggs now could improve your future odds
            </p>
          )}
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
        <div className="mt-3 space-y-3 text-xs text-stone-600">
          <p>
            At age {age}, a single egg-freezing cycle retrieves{" "}
            <strong>{typical} eggs on average</strong> (typical
            range: {rangeLow}&ndash;{rangeHigh}). Individual results
            vary widely based on your ovarian reserve, which a fertility clinic
            can assess with an AMH blood test and antral follicle count.
          </p>
          <p>
            Each frozen egg has roughly a{" "}
            <strong>{Math.round(perOocyte * 100)}% chance</strong> of
            eventually resulting in a live birth (accounting for thaw
            survival, fertilization, and embryo viability). To have a
            ~93% chance of at least one child from frozen eggs alone, you
            would need roughly <strong>{eggsFor93} eggs</strong>
            {eggsFor93 > typical
              ? `, which typically requires ${Math.ceil(eggsFor93 / typical)} IVF cycles`
              : ""}.
            {age < 35
              ? " Freezing before 35 gives the best per-egg odds."
              : age < 38
                ? " Per-egg success rates decline meaningfully after 35."
                : " Per-egg success rates are lower at this age — more eggs or multiple cycles may be needed."}
          </p>
          <p>
            A single egg-freezing cycle in the US typically costs{" "}
            <strong>$10,000&ndash;$15,000</strong> for the retrieval
            procedure, plus <strong>$3,000&ndash;$6,000</strong> for
            medications, and <strong>$500&ndash;$1,000/year</strong> for
            storage.
          </p>
          <p>
            You can increase the theoretical egg count to
            model either the lower end or higher end of a typical egg freezing cycle, or multiple cycles. For example, {typical * 2} eggs
            for two cycles.
          </p>
          <div className="flex items-center gap-2 pt-1">
            <label htmlFor="whatif-num-eggs" className="text-xs text-stone-600">
              Eggs to freeze:
            </label>
            <input
              id="whatif-num-eggs"
              type="number"
              min={1}
              max={40}
              value={numEggs || ""}
              onFocus={(e) => e.target.select()}
              onChange={(e) => {
                const v = e.target.value ? Math.max(1, Math.min(40, +e.target.value)) : 0;
                onNumEggsChange(v);
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
        </div>
      )}
    </div>
  );
}
