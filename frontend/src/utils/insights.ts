import type { FormState, SweepResponse, SweepPoint } from "../api/types";
import { SMOKING_REDUCTIONS } from "../constants/fertility";
import { getBmiReduction } from "../constants/fertility";
import { formatPercent } from "./formatters";

export interface HeroInsight {
  sentiment: "positive" | "moderate" | "cautious";
  headline: string;
  detail: string;
  naturalRate: number | null;
  ivfRate: number | null;
}

export interface DetailInsight {
  id: string;
  text: string;
}

function findPointAtAge(points: SweepPoint[], age: number): SweepPoint | undefined {
  return points.find((p) => Math.abs(p.starting_age - age) < 0.5);
}

function findCutoffAge(points: SweepPoint[], threshold: number): number | null {
  for (let i = 0; i < points.length; i++) {
    const p = points[i];
    if (p && p.completion_rate < threshold) {
      return i > 0 ? points[i - 1]!.starting_age : p.starting_age;
    }
  }
  return null;
}

export function generateHeroInsight(
  form: FormState,
  data: SweepResponse,
): HeroInsight {
  const children = form.desired_children;
  const childWord = children === 1 ? "child" : "children";
  const target = form.acceptable_probability;
  const showIvf = form.ivf_willingness !== "no";

  const natPoint = findPointAtAge(data.scenarios.natural_only, form.user_age);
  const ivfPoint = showIvf
    ? findPointAtAge(data.scenarios.with_ivf, form.user_age)
    : null;

  const natRate = natPoint?.completion_rate ?? 0;
  const ivfRate = ivfPoint?.completion_rate ?? null;

  // Use the best available rate for sentiment
  const bestRate = ivfRate !== null ? Math.max(natRate, ivfRate) : natRate;

  const natCutoff = findCutoffAge(data.scenarios.natural_only, target);

  let sentiment: HeroInsight["sentiment"];
  let headline: string;
  let detail: string;

  if (bestRate >= target) {
    sentiment = "positive";
    const yearsLeft = natCutoff ? natCutoff - form.user_age : null;
    // Pick phrasing based on how far above the target the natural rate is
    const margin = natRate - target;
    const abovePhrase =
      margin >= 0.1 ? "well above" : margin >= 0.03 ? "above" : "around";

    if (showIvf) {
      headline = `${formatPercent(natRate)} chance naturally`;
      detail =
        yearsLeft !== null && yearsLeft > 0
          ? `At ${form.user_age}, you have strong odds of having ${children} ${childWord}. You could wait ~${Math.round(yearsLeft)} more years naturally and still meet your ${formatPercent(target)} target.`
          : `At ${form.user_age}, your natural conception odds are ${abovePhrase} your ${formatPercent(target)} target.`;
    } else {
      headline = `${formatPercent(natRate)} chance of having ${children} ${childWord}`;
      detail =
        yearsLeft !== null && yearsLeft > 0
          ? `At ${form.user_age}, you have strong odds. You could wait ~${Math.round(yearsLeft)} more years and still meet your ${formatPercent(target)} target.`
          : `At ${form.user_age}, your projected completion rate is ${abovePhrase} your ${formatPercent(target)} target.`;
    }
  } else if (bestRate >= 0.5) {
    sentiment = "moderate";

    if (showIvf) {
      headline = `${formatPercent(natRate)} chance naturally`;
      detail = `At ${form.user_age}, your natural odds are below your ${formatPercent(target)} target. ${
        natCutoff
          ? `Starting by age ${natCutoff} would meet that threshold naturally.`
          : "Consider starting sooner to improve your chances."
      }`;
    } else {
      headline = `${formatPercent(natRate)} chance of having ${children} ${childWord}`;
      detail = `At ${form.user_age}, your odds are good but below your ${formatPercent(target)} target. ${
        natCutoff
          ? `Starting by age ${natCutoff} would meet that threshold.`
          : "Consider starting sooner to improve your chances."
      }`;
    }
  } else {
    sentiment = "cautious";

    if (showIvf) {
      headline = `${formatPercent(natRate)} chance naturally`;
      detail = `At ${form.user_age}, completing ${children} ${childWord} naturally is challenging. Each year of earlier start meaningfully improves your odds.`;
    } else {
      headline = `${formatPercent(natRate)} chance of having ${children} ${childWord}`;
      detail = `At ${form.user_age}, completing ${children} ${childWord} is more challenging. Considering IVF could significantly improve your projected outcome.`;
    }
  }

  return { sentiment, headline, detail, naturalRate: natRate, ivfRate };
}

export function generateDetailedInsights(
  form: FormState,
  data: SweepResponse,
): DetailInsight[] {
  const insights: DetailInsight[] = [];
  const userPoint = findPointAtAge(data.results, form.user_age);
  const rate = userPoint ? formatPercent(userPoint.completion_rate) : "N/A";
  const children = form.desired_children;
  const childWord = children === 1 ? "child" : "children";

  // Always: current age odds
  insights.push({
    id: "current-odds",
    text: `Starting at age ${form.user_age} gives you a ${rate} chance of having ${children} ${childWord} with your current settings.`,
  });

  // Always: 90% cutoff
  const cutoff90 = findCutoffAge(data.results, 0.9);
  if (cutoff90) {
    insights.push({
      id: "cutoff-90",
      text: `To achieve 90% confidence of completing your family, the model suggests starting by age ${cutoff90}.`,
    });
  }

  // IVF benefit
  if (form.ivf_willingness !== "no") {
    const natPoint = findPointAtAge(data.scenarios.natural_only, form.user_age);
    const ivfPoint = findPointAtAge(data.scenarios.with_ivf, form.user_age);
    if (natPoint && ivfPoint) {
      const natCutoff = findCutoffAge(data.scenarios.natural_only, 0.5);
      const ivfCutoff = findCutoffAge(data.scenarios.with_ivf, 0.5);
      if (natCutoff && ivfCutoff) {
        const yearsGained = ivfCutoff - natCutoff;
        if (yearsGained > 0) {
          insights.push({
            id: "ivf-benefit",
            text: `IVF extends your reproductive window by approximately ${Math.round(yearsGained)} years (50% completion threshold shifts from age ${natCutoff} to ${ivfCutoff}).`,
          });
        }
      }
    }
  }

  // Frozen benefit
  if (
    data.scenarios.with_frozen &&
    (form.frozen_egg_batches.length > 0 || form.frozen_embryo_batches.length > 0)
  ) {
    const ivfPoint = findPointAtAge(data.scenarios.with_ivf, form.user_age);
    const frozenPoint = findPointAtAge(data.scenarios.with_frozen, form.user_age);
    if (ivfPoint && frozenPoint) {
      insights.push({
        id: "frozen-benefit",
        text: `Your frozen reserves improve your odds at age ${form.user_age} from ${formatPercent(ivfPoint.completion_rate)} to ${formatPercent(frozenPoint.completion_rate)}.`,
      });
    }
  }

  // Cycles tried
  if (form.cycles_tried > 0) {
    insights.push({
      id: "cycles-tried",
      text: `Having tried ${form.cycles_tried} cycle${form.cycles_tried > 1 ? "s" : ""} without conception, the model has adjusted your estimated fecundability downward to reflect this.`,
    });
  }

  // Smoking
  if (form.smoking_status !== "never") {
    const reduction = SMOKING_REDUCTIONS[form.smoking_status] ?? 0;
    if (reduction > 0) {
      insights.push({
        id: "smoking",
        text: `Your smoking status is associated with approximately ${reduction}% reduction in cycle-level conception probability.`,
      });
    }
  }

  // BMI
  if (form.bmi !== null && form.bmi >= 35) {
    const reduction = getBmiReduction(form.bmi);
    insights.push({
      id: "bmi",
      text: `A BMI of ${form.bmi.toFixed(1)} is associated with approximately ${reduction}% reduction in natural conception probability.`,
    });
  }

  // Male age
  if (form.male_age_offset !== null && form.user_age + form.male_age_offset >= 40) {
    insights.push({
      id: "male-age",
      text: `A partner age of ${form.user_age + form.male_age_offset} is associated with increased time to conception and slightly elevated miscarriage risk.`,
    });
  }

  // Prior live births
  if (form.prior_live_births > 0) {
    insights.push({
      id: "proven-fertility",
      text: `Your prior ${form.prior_live_births === 1 ? "birth" : `${form.prior_live_births} births`} indicates proven fertility, which is reflected in a higher fecundability curve.`,
    });
  }

  return insights;
}
