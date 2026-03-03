import { memo } from "react";
import type { FormState, SweepResponse } from "../../api/types";
import { generateHeroInsight, generateDetailedInsights } from "../../utils/insights";
import HeroInsight from "./HeroInsight";
import CompletionChart from "./CompletionChart";
import DetailedInsights from "./DetailedInsights";

interface Props {
  form: FormState;
  data: SweepResponse;
  loading?: boolean;
}

export default memo(function ResultsPanel({ form, data, loading }: Props) {
  const heroInsight = generateHeroInsight(form, data);
  const detailedInsights = generateDetailedInsights(form, data);

  const showIvf = form.ivf_willingness !== "no";
  const hasFrozen =
    form.frozen_egg_batches.length > 0 || form.frozen_embryo_batches.length > 0;

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
          showFrozen={hasFrozen}
        />
        <DetailedInsights insights={detailedInsights} />
      </div>
    </div>
  );
});
