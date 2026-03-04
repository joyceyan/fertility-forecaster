import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { SweepResponse } from "../../api/types";

interface Props {
  data: SweepResponse;
  userAge: number;
  showIvf: boolean;
  showFrozen: boolean;
  frozenLabel?: string;
}

export default function CompletionChart({
  data,
  userAge,
  showIvf,
  showFrozen,
  frozenLabel = "With Frozen Reserves",
}: Props) {
  // Merge scenario data into one array keyed by starting_age
  const merged = useMemo(
    () =>
      data.scenarios.natural_only.map((nat, i) => {
        const ivf = data.scenarios.with_ivf[i];
        const frozen = data.scenarios.with_frozen?.[i];
        return {
          age: nat.starting_age,
          natural: Math.round(nat.completion_rate * 100 * 10) / 10,
          with_ivf: ivf ? Math.round(ivf.completion_rate * 100 * 10) / 10 : undefined,
          with_frozen: frozen
            ? Math.round(frozen.completion_rate * 100 * 10) / 10
            : undefined,
        };
      }),
    [data],
  );

  return (
    <div>
      <h3 className="mb-3 text-sm font-semibold text-stone-700">
        Completion Probability by Starting Age
      </h3>
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={merged} margin={{ top: 20, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e7e5e4" />
          <XAxis
            dataKey="age"
            label={{ value: "Starting Age", position: "insideBottom", offset: -2, style: { fontSize: 12, fill: "#78716c" } }}
            tick={{ fontSize: 11, fill: "#78716c" }}
          />
          <YAxis
            domain={[0, 100]}
            tickFormatter={(v: number) => `${v}%`}
            tick={{ fontSize: 11, fill: "#78716c" }}
          />
          <Tooltip
            formatter={(value: number, name: string) => [
              `${value}%`,
              name === "natural"
                ? "Natural"
                : name === "with_ivf"
                  ? "With IVF"
                  : frozenLabel,
            ]}
            labelFormatter={(label: number) => `Age ${label}`}
          />
          <Legend
            verticalAlign="top"
            wrapperStyle={{ paddingBottom: 16 }}
            formatter={(value: string) =>
              value === "natural"
                ? "Natural"
                : value === "with_ivf"
                  ? "With IVF"
                  : frozenLabel
            }
          />

          {/* Horizontal reference lines */}
          <ReferenceLine y={90} stroke="#d6d3d1" strokeDasharray="6 3" />
          <ReferenceLine y={75} stroke="#d6d3d1" strokeDasharray="6 3" />
          <ReferenceLine y={50} stroke="#d6d3d1" strokeDasharray="6 3" />

          {/* Vertical line at user's current age */}
          <ReferenceLine
            x={userAge}
            stroke="#78716c"
            strokeDasharray="4 4"
            strokeWidth={2}
            label={{
              value: `You (${userAge})`,
              position: "top",
              style: { fontSize: 11, fill: "#78716c", fontWeight: 600 },
            }}
          />

          <Line
            type="monotone"
            dataKey="natural"
            stroke="#d4a574"
            strokeWidth={2.5}
            dot={false}
            animationDuration={800}
          />
          {showIvf && (
            <Line
              type="monotone"
              dataKey="with_ivf"
              stroke="#7c6f8a"
              strokeWidth={2}
              strokeDasharray="8 4"
              dot={false}
              animationDuration={800}
            />
          )}
          {showFrozen && data.scenarios.with_frozen && (
            <Line
              type="monotone"
              dataKey="with_frozen"
              stroke="#6b9e8a"
              strokeWidth={2}
              strokeDasharray="3 3"
              dot={false}
              animationDuration={800}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
