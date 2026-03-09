"""Benchmark our model against Habbema et al. 2015 cutoff ages.

Habbema reports the latest age at which couples can start trying and still
achieve their desired family size at 50%, 75%, and 90% confidence, for 1-3
children, with and without IVF.

This script finds our model's cutoff ages for all 18 combinations and
compares them to Habbema's published values.
"""

from fertility_forecaster.models import SimulationParams
from fertility_forecaster.simulation import run_simulation

# Habbema et al. 2015, Table from the paper
HABBEMA = {
    # (children, threshold, ivf): cutoff_age
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


def find_cutoff(desired_children: int, threshold: float, ivf: bool) -> tuple[float, float]:
    """Find the latest starting age where completion rate >= threshold.

    Returns (cutoff_age, rate_at_cutoff).
    Scans from age 18 upward in 0.1-year steps.
    """
    last_passing_age = 18.0
    last_passing_rate = 0.0
    for age_10x in range(180, 451):
        age = age_10x / 10.0
        result = run_simulation(
            SimulationParams(
                female_age=age,
                desired_children=desired_children,
                ivf_willingness="yes" if ivf else "no",
            )
        )
        if result.completion_rate >= threshold:
            last_passing_age = age
            last_passing_rate = result.completion_rate
        elif last_passing_age > 18.0:
            # We've passed the cutoff
            break
    return last_passing_age, last_passing_rate


def main():
    print("=" * 80)
    print("Habbema et al. 2015 Benchmark Comparison")
    print("=" * 80)

    for ivf in [False, True]:
        ivf_label = "With IVF" if ivf else "Without IVF"
        print(f"\n{'─' * 80}")
        print(f"  {ivf_label}")
        print(f"{'─' * 80}")
        print(f"  {'Threshold':<12} {'Children':<10} {'Habbema':<10} {'Ours':<10} {'Delta':<10} {'Rate':<10}")
        print(f"  {'─'*12} {'─'*10} {'─'*10} {'─'*10} {'─'*10} {'─'*10}")

        for threshold in [0.50, 0.75, 0.90]:
            for children in [1, 2, 3]:
                habbema_age = HABBEMA[(children, threshold, ivf)]
                our_age, our_rate = find_cutoff(children, threshold, ivf)
                delta = our_age - habbema_age
                sign = "+" if delta >= 0 else ""
                print(
                    f"  {threshold:<12.0%} {children:<10} {habbema_age:<10} {our_age:<10.1f} {sign}{delta:<9.1f} {our_rate:<10.1%}"
                )

    print(f"\n{'=' * 80}")


if __name__ == "__main__":
    main()
