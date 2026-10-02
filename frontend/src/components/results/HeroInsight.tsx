import { useExperiment, defineExperiment, assertNever } from "@trevosdk/react";
import type { HeroInsight as HeroInsightData } from "../../utils/insights";
import { formatPercent } from "../../utils/formatters";
import ForecastContextVariant from "./ForecastContextVariant";

interface Props {
  insight: HeroInsightData;
}

const SENTIMENT_STYLES = {
  positive: "border-sage-green/30 bg-sage-green/5",
  moderate: "border-warm-gold/30 bg-warm-gold/5",
  cautious: "border-muted-purple/30 bg-muted-purple/5",
} as const;

const forecastContextExperiment = defineExperiment(
  "explain-the-forecast-beside-its-headline",
  ["control", "variant"],
);

export default function HeroInsight({ insight }: Props) {
  const variant = useExperiment(forecastContextExperiment);

  if (variant === "variant") {
    return (
      <div
        className={`rounded-xl border-2 p-6 ${SENTIMENT_STYLES[insight.sentiment]}`}
      >
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-2xl font-bold text-stone-800">{insight.headline}</p>

            {insight.ivfRate !== null && (
              <p className="mt-1 text-sm font-medium text-stone-500">
                With IVF as a fallback: {formatPercent(insight.ivfRate)}
              </p>
            )}
          </div>

          <ForecastContextVariant methodologyHref="/methodology.html" />
        </div>
      </div>
    );
  }

  if (variant !== "control") {
    return assertNever(variant);
  }

  return (
    <div
      className={`rounded-xl border-2 p-6 ${SENTIMENT_STYLES[insight.sentiment]}`}
    >
      <p className="text-2xl font-bold text-stone-800">{insight.headline}</p>

      {insight.ivfRate !== null && (
        <p className="mt-1 text-sm font-medium text-stone-500">
          With IVF as a fallback: {formatPercent(insight.ivfRate)}
        </p>
      )}
    </div>
  );
}
