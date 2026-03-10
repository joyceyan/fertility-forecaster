"""Benchmark Beta distribution CV options for fecundability against Habbema.

Tests CVs from 0.50 to 0.80, computing the corresponding Beta concentration
parameter and comparing cutoff ages against all 18 Habbema benchmarks.

Math: For Beta(α, β) with mean=m:
  CV = sqrt((1-m) / (m * (conc + 1)))
  conc = (1-m)/(m*CV²) - 1

Usage:
  cd backend && python -m scripts.test_concentrations
"""

import math
import sys
import time

import numpy as np

import fertility_forecaster.curves as curves
from fertility_forecaster.models import SimulationParams
from fertility_forecaster.simulation import run_simulation


def log(msg=""):
    print(msg, flush=True)


# Habbema et al. 2015 published cutoff ages
# (children, threshold, ivf): cutoff_age
HABBEMA = {
    (1, 0.50, False): 41,
    (1, 0.75, False): 37,
    (1, 0.90, False): 32,
    (2, 0.50, False): 38,
    (2, 0.75, False): 34,
    (2, 0.90, False): 27,
    (3, 0.50, False): 35,
    (3, 0.75, False): 31,
    (3, 0.90, False): 23,
    (1, 0.50, True): 42,
    (1, 0.75, True): 39,
    (1, 0.90, True): 35,
    (2, 0.50, True): 39,
    (2, 0.75, True): 35,
    (2, 0.90, True): 31,
    (3, 0.50, True): 36,
    (3, 0.75, True): 33,
    (3, 0.90, True): 28,
}

# CVs to test
TEST_CVS = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]

# Must match _BASE_FECUNDABILITY in curves.py
BASE_MEAN = 0.23


def cv_to_concentration(cv: float, mean: float = BASE_MEAN) -> float:
    """Convert CV to Beta concentration parameter.

    For Beta(α, β) with α = mean*conc, β = (1-mean)*conc:
      Var = mean*(1-mean)/(conc+1)
      CV  = sqrt(Var)/mean = sqrt((1-mean)/(mean*(conc+1)))
      conc = (1-mean)/(mean*CV²) - 1
    """
    return (1.0 - mean) / (mean * cv * cv) - 1.0


def find_cutoff(desired_children: int, threshold: float, ivf: bool) -> tuple[float, float]:
    """Find the latest starting age where completion rate >= threshold."""
    last_passing_age = 18.0
    last_passing_rate = 0.0
    for age_10x in range(180, 451):
        age = age_10x / 10.0
        # Match Habbema's IVF timing protocol
        habbema_cycles_before_ivf = 12
        if age <= 33:
            habbema_cycles_before_ivf = 36
        elif age <= 38:
            habbema_cycles_before_ivf = 24
        result = run_simulation(
            SimulationParams(
                female_age=age,
                desired_children=desired_children,
                ivf_willingness="yes" if ivf else "no",
                cycles_before_ivf=habbema_cycles_before_ivf,
            )
        )
        if result.completion_rate >= threshold:
            last_passing_age = age
            last_passing_rate = result.completion_rate
        elif last_passing_age > 18.0:
            break
    return last_passing_age, last_passing_rate


def distribution_percentiles(concentration: float, mean: float = BASE_MEAN) -> dict[str, float]:
    """Compute percentiles of Beta(mean*conc, (1-mean)*conc)."""
    from scipy.stats import beta as beta_dist
    alpha = mean * concentration
    beta_param = (1.0 - mean) * concentration
    pcts = [5, 10, 25, 50, 75, 90, 95]
    vals = beta_dist.ppf([p / 100 for p in pcts], alpha, beta_param)
    return {f"p{p}": v for p, v in zip(pcts, vals)}


def run_for_cv(cv: float) -> dict:
    """Run all 18 Habbema scenarios for a given CV. Returns error metrics."""
    conc = cv_to_concentration(cv)
    original = curves.FECUNDABILITY_CONCENTRATION
    curves.FECUNDABILITY_CONCENTRATION = conc

    log(f"\n{'=' * 80}")
    log(f"  CV = {cv:.2f}  →  Concentration = {conc:.2f}")
    log(f"{'=' * 80}")

    # Show distribution shape
    pcts = distribution_percentiles(conc)
    pct_str = "  ".join(f"{k}={v:.3f}" for k, v in pcts.items())
    log(f"  Distribution shape: {pct_str}")

    errors = []

    for ivf in [False, True]:
        ivf_label = "With IVF" if ivf else "Without IVF"
        log(f"\n  {ivf_label}")
        log(f"  {'Thresh':<8} {'Kids':<6} {'Habbema':<9} {'Ours':<9} {'Delta':<8} {'AbsErr':<8}")
        log(f"  {'─' * 8} {'─' * 6} {'─' * 9} {'─' * 9} {'─' * 8} {'─' * 8}")

        for threshold in [0.50, 0.75, 0.90]:
            for children in [1, 2, 3]:
                habbema_age = HABBEMA[(children, threshold, ivf)]
                our_age, _ = find_cutoff(children, threshold, ivf)
                delta = our_age - habbema_age
                abs_err = abs(delta)
                errors.append(delta)
                sign = "+" if delta >= 0 else ""
                log(
                    f"  {threshold:<8.0%} {children:<6} {habbema_age:<9} "
                    f"{our_age:<9.1f} {sign}{delta:<7.1f} {abs_err:<8.1f}"
                )

    curves.FECUNDABILITY_CONCENTRATION = original

    abs_errors = [abs(e) for e in errors]
    mae = sum(abs_errors) / len(abs_errors)
    max_err = max(abs_errors)
    rmse = math.sqrt(sum(e * e for e in errors) / len(errors))

    log(f"\n  Summary: MAE={mae:.2f}  MaxErr={max_err:.1f}  RMSE={rmse:.2f}")

    return {
        "cv": cv,
        "concentration": conc,
        "mae": mae,
        "max_err": max_err,
        "rmse": rmse,
        "errors": errors,
    }


def main():
    log("Benchmarking Beta Distribution CV Options for Fecundability")
    log("=" * 80)
    log()
    log(f"CV-to-Concentration mapping (mean={BASE_MEAN}):")
    for cv in TEST_CVS:
        conc = cv_to_concentration(cv)
        log(f"  CV={cv:.2f}  →  conc={conc:.2f}")
    log()

    t0 = time.time()
    results = []
    for cv in TEST_CVS:
        cv_t0 = time.time()
        r = run_for_cv(cv)
        r["time"] = time.time() - cv_t0
        results.append(r)
        log(f"  Time: {r['time']:.1f}s")

    total_time = time.time() - t0

    # Final summary table
    log(f"\n\n{'=' * 80}")
    log("SUMMARY: All CVs Ranked by MAE")
    log(f"{'=' * 80}")
    log(f"  {'CV':<6} {'Conc':<8} {'MAE':<8} {'MaxErr':<8} {'RMSE':<8} {'Time':<8}")
    log(f"  {'─' * 6} {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 8}")

    ranked = sorted(results, key=lambda r: r["mae"])
    for r in ranked:
        marker = " ←" if r is ranked[0] else ""
        log(
            f"  {r['cv']:<6.2f} {r['concentration']:<8.2f} "
            f"{r['mae']:<8.2f} {r['max_err']:<8.1f} {r['rmse']:<8.2f} "
            f"{r['time']:<8.1f}s{marker}"
        )

    log(f"\n  Best CV: {ranked[0]['cv']:.2f} (concentration={ranked[0]['concentration']:.2f})")
    log(f"  Total time: {total_time:.0f}s")

    # Distribution shape comparison
    log(f"\n{'=' * 80}")
    log("Distribution Shape Comparison (percentiles of Beta distribution)")
    log(f"{'=' * 80}")
    log(f"  {'CV':<6} {'Conc':<7} {'p5':<7} {'p10':<7} {'p25':<7} {'p50':<7} {'p75':<7} {'p90':<7} {'p95':<7}")
    log(f"  {'─' * 6} {'─' * 7} {'─' * 7} {'─' * 7} {'─' * 7} {'─' * 7} {'─' * 7} {'─' * 7} {'─' * 7}")
    for r in results:
        pcts = distribution_percentiles(r["concentration"])
        log(
            f"  {r['cv']:<6.2f} {r['concentration']:<7.2f} "
            + " ".join(f"{v:<7.3f}" for v in pcts.values())
        )

    log()


if __name__ == "__main__":
    main()
