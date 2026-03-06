import { memo } from "react";
import type { FormState, SweepResponse } from "../../api/types";
import { generateHeroInsight } from "../../utils/insights";
import HeroInsight from "./HeroInsight";
import CompletionChart from "./CompletionChart";
import WhatIfFreezeCard from "./WhatIfFreezeCard";

interface WhatIfFreeze {
  enabled: boolean;
  numEggs: number;
}

interface Props {
  form: FormState;
  data: SweepResponse;
  loading?: boolean;
  whatIfFreeze: WhatIfFreeze;
  onWhatIfToggle: (enabled: boolean) => void;
  onWhatIfNumEggs: (numEggs: number) => void;
  onWhatIfApply: () => void;
}

export default memo(function ResultsPanel({
  form,
  data,
  loading,
  whatIfFreeze,
  onWhatIfToggle,
  onWhatIfNumEggs,
  onWhatIfApply,
}: Props) {
  const heroInsight = generateHeroInsight(form, data);

  const hasFrozen =
    form.frozen_egg_batches.length > 0 || form.frozen_embryo_batches.length > 0;
  const showFrozen = hasFrozen || whatIfFreeze.enabled;

  const frozenLabel = whatIfFreeze.enabled
    ? hasFrozen
      ? "With frozen reserves + new freeze"
      : `With egg freeze at ${form.user_age}`
    : "With Frozen Reserves";

  const showIvf = form.ivf_willingness !== "no";

  return (
    <div className="relative">
      {loading && (
        <div className="absolute inset-0 z-10 flex items-center justify-center rounded-lg bg-white/70">
          <div className="flex items-center gap-2 text-stone-400">
            <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <span className="text-sm font-medium">Recalculating...</span>
          </div>
        </div>
      )}
      <div className={`space-y-8 transition-opacity duration-200 ${loading ? "opacity-40" : ""}`}>
        <HeroInsight insight={heroInsight} />
        <CompletionChart
          data={data}
          userAge={form.user_age}
          showIvf={showIvf}
          showFrozen={showFrozen}
          frozenLabel={frozenLabel}
        />
        <WhatIfFreezeCard
          age={form.user_age}
          enabled={whatIfFreeze.enabled}
          numEggs={whatIfFreeze.numEggs}
          onToggle={onWhatIfToggle}
          onNumEggsChange={onWhatIfNumEggs}
          onApply={onWhatIfApply}
        />
      </div>
    </div>
  );
});
