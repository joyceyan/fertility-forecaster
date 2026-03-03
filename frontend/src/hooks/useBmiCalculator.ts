import { useMemo, useState } from "react";

type Unit = "imperial" | "metric";

interface BmiCalculator {
  unit: Unit;
  setUnit: (u: Unit) => void;
  heightFeet: number;
  setHeightFeet: (v: number) => void;
  heightInches: number;
  setHeightInches: (v: number) => void;
  heightCm: number;
  setHeightCm: (v: number) => void;
  weightLbs: number;
  setWeightLbs: (v: number) => void;
  weightKg: number;
  setWeightKg: (v: number) => void;
  bmi: number | null;
}

export function useBmiCalculator(): BmiCalculator {
  const [unit, setUnit] = useState<Unit>("imperial");
  const [heightFeet, setHeightFeet] = useState(5);
  const [heightInches, setHeightInches] = useState(5);
  const [heightCm, setHeightCm] = useState(165);
  const [weightLbs, setWeightLbs] = useState(140);
  const [weightKg, setWeightKg] = useState(64);

  const bmi = useMemo(() => {
    if (unit === "imperial") {
      const totalInches = heightFeet * 12 + heightInches;
      if (totalInches <= 0 || weightLbs <= 0) return null;
      return (weightLbs * 703) / (totalInches * totalInches);
    } else {
      if (heightCm <= 0 || weightKg <= 0) return null;
      const meters = heightCm / 100;
      return weightKg / (meters * meters);
    }
  }, [unit, heightFeet, heightInches, heightCm, weightLbs, weightKg]);

  return {
    unit,
    setUnit,
    heightFeet,
    setHeightFeet,
    heightInches,
    setHeightInches,
    heightCm,
    setHeightCm,
    weightLbs,
    setWeightLbs,
    weightKg,
    setWeightKg,
    bmi: bmi !== null ? Math.round(bmi * 10) / 10 : null,
  };
}
