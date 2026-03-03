import type { DetailInsight } from "../../utils/insights";

interface Props {
  insights: DetailInsight[];
}

export default function DetailedInsights({ insights }: Props) {
  if (insights.length === 0) return null;

  return (
    <div>
      <h3 className="mb-3 text-sm font-semibold text-stone-700">
        Detailed Insights
      </h3>
      <div className="space-y-2">
        {insights.map((insight) => (
          <div
            key={insight.id}
            className="rounded-lg border border-stone-200 bg-white p-4 text-sm leading-relaxed text-stone-600"
          >
            {insight.text}
          </div>
        ))}
      </div>
    </div>
  );
}
