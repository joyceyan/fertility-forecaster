#!/usr/bin/env python3
"""Reverse-engineer Habbema's fecundability decline curve from published data.

Loads approximate completion rate data digitized from Habbema 2015 figures,
then optimizes a fecundability decline curve to best-fit that data using
a standalone Habbema-faithful simulation.

Tests both Beta and truncated Normal fecundability distributions.

Key design:
- Vectorize ALL start ages into one giant simulation array (38K couples).
- Fecundability heterogeneity drawn at BASE level (age 20-30), then scaled by
  curve(age)/BASE_FECUND. This correctly handles all start ages.
- MAX_AGE=50 to allow late starters realistic chances. Sterility curve
  handles biological cutoff.
"""

import csv
import sys
import time

import numpy as np
from scipy import optimize
from scipy.stats import truncnorm

# ─── Known Habbema parameters ───────────────────────────────────────────────

BASE_FECUND = 0.23
FECUND_CV = 0.52

# Extended to age 50
MISCARRIAGE_AGES = np.array([20, 25, 30, 35, 40, 45, 50], dtype=float)
MISCARRIAGE_RATES = np.array([0.12, 0.13, 0.15, 0.18, 0.25, 0.35, 0.50])

STERILITY_AGES = np.array([20, 25, 30, 35, 38, 40, 42, 45, 48, 50], dtype=float)
STERILITY_RATES = np.array([0.005, 0.01, 0.02, 0.05, 0.10, 0.17, 0.30, 0.55, 0.80, 0.95])

# IVF — age-dependent LBR (Netherlands 2013), zero beyond 45
IVF_AGES = np.array([25, 30, 35, 40, 45, 50], dtype=float)
IVF_RATES = np.array([0.32, 0.35, 0.30, 0.15, 0.05, 0.0])

MAX_IVF_CYCLES = 3
IVF_CYCLE_MONTHS = 4
MIN_SPACING = 15
MISCARRIAGE_RECOVERY = 3
MAX_AGE = 50.0

# Fecundability knots: 7 free params at [32..44], ≤30 fixed, >44 clamped
KNOT_AGES = np.array([20, 30, 32, 34, 36, 38, 40, 42, 44], dtype=float)


# ─── Load target data ───────────────────────────────────────────────────────

def load_target_data(path):
    targets = {}
    with open(path) as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [h.strip() for h in reader.fieldnames]
        for row in reader:
            age = int(row["age"])
            targets[age] = {}
            for children in [1, 2, 3]:
                for ivf_label, use_ivf in [("ivf", True), ("no ivf", False)]:
                    key = f"{children} ({ivf_label})"
                    targets[age][(children, use_ivf)] = float(row[key]) / 100.0
    return targets


# ─── Distribution draw functions ────────────────────────────────────────────

def draw_beta(mean, cv, n, rng):
    var = (mean * cv) ** 2
    concentration = mean * (1 - mean) / var - 1
    a = mean * concentration
    b = (1 - mean) * concentration
    return rng.beta(a, b, size=n)


def draw_truncnorm(mean, cv, n, rng):
    sd = mean * cv
    a_clip = (0 - mean) / sd
    b_clip = (1 - mean) / sd
    return truncnorm.rvs(a_clip, b_clip, loc=mean, scale=sd, size=n,
                         random_state=rng)


# ─── Curve builders & interpolation ─────────────────────────────────────────

def build_decline_curve(knot_values):
    """7 knot values at [32,34,36,38,40,42,44]. ≤30=BASE_FECUND. >44 clamped."""
    all_values = np.array([BASE_FECUND, BASE_FECUND] + list(knot_values))
    def curve(ages):
        return np.interp(ages, KNOT_AGES, all_values)
    return curve


def miscarriage_rate(ages):
    return np.interp(ages, MISCARRIAGE_AGES, MISCARRIAGE_RATES)

def sterility_prob(ages):
    return np.interp(ages, STERILITY_AGES, STERILITY_RATES)

def ivf_success_rate(ages):
    return np.interp(ages, IVF_AGES, IVF_RATES)


# ─── Vectorized simulation across all start ages ────────────────────────────

def simulate_all_ages(start_ages, use_ivf, fecund_curve, dist_type,
                      N_per_age=2000, seed=42):
    """Run Habbema simulation for ALL start ages in one vectorized loop.

    Fecundability heterogeneity is drawn at the BASE level (age 20-30) and
    scaled by curve(age)/BASE_FECUND at each time step.

    Returns dict: {age: (rate_1child, rate_2child, rate_3child)}.
    """
    n_ages = len(start_ages)
    N = n_ages * N_per_age
    rng = np.random.default_rng(seed)

    # Draw baseline fecundabilities (heterogeneity at reference age 20-30)
    if dist_type == "beta":
        individual_fecund = draw_beta(BASE_FECUND, FECUND_CV, N, rng)
    else:
        individual_fecund = draw_truncnorm(BASE_FECUND, FECUND_CV, N, rng)

    age = np.repeat(np.array(start_ages, dtype=float), N_per_age).copy()
    children_born = np.zeros(N, dtype=int)
    cycles_tried = np.zeros(N, dtype=int)
    active = np.ones(N, dtype=bool)
    waiting_months = np.zeros(N, dtype=int)
    on_ivf = np.zeros(N, dtype=bool)
    ivf_cycles_used = np.zeros(N, dtype=int)
    ivf_exhausted = np.zeros(N, dtype=bool)
    last_birth_was_ivf = np.zeros(N, dtype=bool)
    sterility_thresholds = rng.random(N)
    already_sterile = np.zeros(N, dtype=bool)

    for _ in range(450):
        if not np.any(active):
            break

        too_old = active & (age >= MAX_AGE)
        active[too_old] = False

        is_waiting = active & (waiting_months > 0)
        waiting_months[is_waiting] -= 1
        age[is_waiting] += 1.0 / 12.0

        trying = active & (waiting_months <= 0) & ~is_waiting
        if not np.any(trying):
            continue

        # Sterility
        cur_ster = sterility_prob(age)
        newly_sterile = trying & ~already_sterile & (cur_ster >= sterility_thresholds)
        already_sterile |= newly_sterile

        # IVF eligibility
        if use_ivf:
            ivf_threshold = np.where(age <= 33, 36, np.where(age < 38, 24, 12))
            eligible = (
                trying & ~on_ivf & ~ivf_exhausted
                & ((cycles_tried >= ivf_threshold) | last_birth_was_ivf)
            )
            on_ivf[eligible] = True

        was_on_ivf = trying & on_ivf

        # Conception probabilities
        p_conceive = np.zeros(N, dtype=float)

        # Natural: p = individual_fecund × curve(age) / BASE_FECUND
        natural = trying & ~on_ivf
        if np.any(natural):
            cur_mean = fecund_curve(age[natural])
            ratio = cur_mean / BASE_FECUND
            p = individual_fecund[natural] * ratio
            p[already_sterile[natural]] = 0.0
            p_conceive[natural] = p

        # IVF: age-dependent LBR (already a live birth rate, no miscarriage roll)
        if np.any(was_on_ivf):
            p_conceive[was_on_ivf] = ivf_success_rate(age[was_on_ivf])

        np.clip(p_conceive, 0.0, 1.0, out=p_conceive)
        conceived = trying & (rng.random(N) < p_conceive)

        # Miscarriage on natural conceptions only
        natural_conceived = conceived & ~was_on_ivf
        p_misc = miscarriage_rate(age)
        miscarried = natural_conceived & (rng.random(N) < p_misc)
        live_birth = (natural_conceived & ~miscarried) | (conceived & was_on_ivf)

        if np.any(live_birth):
            last_birth_was_ivf[live_birth] = was_on_ivf[live_birth]
            children_born[live_birth] += 1
            waiting_months[live_birth] = MIN_SPACING
            cycles_tried[live_birth] = 0
            on_ivf[live_birth] = False
            ivf_cycles_used[live_birth] = 0
            ivf_exhausted[live_birth] = False
            done = live_birth & (children_born >= 3)
            active[done] = False

        if np.any(miscarried):
            waiting_months[miscarried] = MISCARRIAGE_RECOVERY

        no_conception = trying & ~conceived
        cycles_tried[no_conception] += 1

        ivf_fail = no_conception & was_on_ivf
        ivf_cycles_used[ivf_fail] += 1
        exhausted = ivf_fail & (ivf_cycles_used >= MAX_IVF_CYCLES)
        on_ivf[exhausted] = False
        ivf_exhausted[exhausted] = True

        # Age advance: IVF cycles = 4 months, natural = 1 month
        age[was_on_ivf] += IVF_CYCLE_MONTHS / 12.0
        age[trying & ~was_on_ivf] += 1.0 / 12.0

    children = children_born.reshape(n_ages, N_per_age)
    results = {}
    for i, a in enumerate(start_ages):
        results[a] = (
            float(np.mean(children[i] >= 1)),
            float(np.mean(children[i] >= 2)),
            float(np.mean(children[i] >= 3)),
        )
    return results


# ─── Objective function ─────────────────────────────────────────────────────

def compute_sse(targets, fecund_curve, dist_type, N_per_age, seed):
    ages = sorted(targets.keys())
    sse = 0.0
    for use_ivf in [True, False]:
        results = simulate_all_ages(ages, use_ivf, fecund_curve, dist_type,
                                    N_per_age=N_per_age, seed=seed)
        for age in ages:
            r1, r2, r3 = results[age]
            rates = {1: r1, 2: r2, 3: r3}
            for ch in [1, 2, 3]:
                target = targets[age][(ch, use_ivf)]
                sse += (rates[ch] - target) ** 2
    return sse


# ─── Parameterization helpers ───────────────────────────────────────────────

def logistic_decline(ages, k, a0):
    return np.where(
        ages <= 30, BASE_FECUND,
        np.maximum(BASE_FECUND / (1 + np.exp(k * (ages - a0))), 0.001)
    )


def knots_from_cumulative_fractions(fracs):
    """7 values in [0,1] → monotonically decreasing knot values."""
    values = []
    prev = BASE_FECUND
    for f in fracs:
        val = prev - f * (prev - 0.001)
        values.append(val)
        prev = val
    return values


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else \
        "/Users/jyan/Downloads/Habbema2015ApproximateData.csv"
    targets = load_target_data(csv_path)
    n_pts = sum(len(v) for v in targets.values())
    print(f"Loaded {len(targets)} ages × 6 scenarios = {n_pts} data points")

    OPT_N = 2000
    VAL_N = 10000
    SEED = 42

    # Benchmark
    print("\nBenchmarking...")
    test_curve = build_decline_curve([0.22, 0.20, 0.17, 0.13, 0.08, 0.04, 0.01])
    t0 = time.time()
    test_sse = compute_sse(targets, test_curve, "beta", OPT_N, SEED)
    bench = time.time() - t0
    print(f"  One eval: {bench:.2f}s, SSE={test_sse:.4f}")

    best_overall = {"sse": float("inf")}

    for dist_type in ["beta", "truncnorm"]:
        print(f"\n{'='*70}")
        print(f"Distribution: {dist_type}")
        print(f"{'='*70}")

        eval_count = [0]
        def log_eval(sse):
            eval_count[0] += 1
            if eval_count[0] % 10 == 0:
                print(f"  [eval {eval_count[0]}] SSE={sse:.6f}", flush=True)

        # ── Phase 1: Logistic fit (2 params) ──
        print("\nPhase 1: Logistic decline (k, a0)...", flush=True)
        t0 = time.time()
        eval_count[0] = 0

        def logistic_objective(x):
            k, a0 = x
            if k < 0 or a0 < 25 or a0 > 50:
                return 1e6
            curve = lambda ages, _k=k, _a0=a0: logistic_decline(ages, _k, _a0)
            sse = compute_sse(targets, curve, dist_type, OPT_N, SEED)
            log_eval(sse)
            return sse

        res1 = optimize.minimize(
            logistic_objective, x0=[0.3, 38], method="Nelder-Mead",
            options={"maxiter": 80, "xatol": 0.02, "fatol": 0.001}
        )
        k_best, a0_best = res1.x
        print(f"\n  Best: k={k_best:.4f}, a0={a0_best:.2f}, SSE={res1.fun:.6f}, "
              f"evals={eval_count[0]}, time={time.time()-t0:.0f}s")

        knot_ages_fit = [32, 34, 36, 38, 40, 42, 44]
        logistic_at_knots = logistic_decline(np.array(knot_ages_fit), k_best, a0_best)
        print(f"  At knots: {[f'{v:.4f}' for v in logistic_at_knots]}")

        # Convert to cumulative fractions for Phase 2 init
        init_fracs = []
        prev = BASE_FECUND
        for v in logistic_at_knots:
            v_clamped = max(0.001, min(prev, v))
            frac = (prev - v_clamped) / (prev - 0.001) if prev > 0.001 else 0.0
            init_fracs.append(np.clip(frac, 0.01, 0.99))
            prev = v_clamped

        # ── Phase 2: Piecewise linear fit (7 params) ──
        print("\nPhase 2: Piecewise linear (7 knots)...", flush=True)
        t0 = time.time()
        eval_count[0] = 0

        def piecewise_objective(x):
            fracs = 1 / (1 + np.exp(-x))
            knot_values = knots_from_cumulative_fractions(fracs)
            curve = build_decline_curve(knot_values)
            sse = compute_sse(targets, curve, dist_type, OPT_N, SEED)
            log_eval(sse)
            return sse

        init_logits = np.log(np.array(init_fracs) / (1 - np.array(init_fracs)))

        res2 = optimize.minimize(
            piecewise_objective, x0=init_logits, method="Nelder-Mead",
            options={"maxiter": 200, "xatol": 0.02, "fatol": 0.001}
        )

        best_fracs = 1 / (1 + np.exp(-res2.x))
        best_knots = knots_from_cumulative_fractions(best_fracs)
        print(f"\n  SSE={res2.fun:.6f}, evals={eval_count[0]}, time={time.time()-t0:.0f}s")
        for a, v in zip(knot_ages_fit, best_knots):
            print(f"    age {a}: {v:.4f}")

        if res2.fun <= res1.fun:
            best_sse = res2.fun
            best_curve = build_decline_curve(best_knots)
            best_knots_list = best_knots
            curve_label = "piecewise"
        else:
            best_sse = res1.fun
            best_curve = lambda ages, _k=k_best, _a0=a0_best: logistic_decline(ages, _k, _a0)
            best_knots_list = list(logistic_at_knots)
            curve_label = "logistic"

        if best_sse < best_overall["sse"]:
            best_overall = {
                "sse": best_sse, "dist_type": dist_type,
                "curve": best_curve, "knots": best_knots_list,
                "curve_type": curve_label,
            }

    # ─── Final validation ────────────────────────────────────────────────
    dist = best_overall["dist_type"]
    ctype = best_overall["curve_type"]
    print(f"\n{'='*70}")
    print(f"BEST FIT: {dist} / {ctype}, SSE={best_overall['sse']:.6f}")
    print(f"{'='*70}")

    print(f"\nFecundability decline curve:")
    print(f"  {'Age':>4}  {'Fecund':>8}")
    for a in [20, 25, 30, 32, 34, 36, 38, 40, 42, 44, 45, 48, 50]:
        v = best_overall["curve"](np.array([float(a)]))[0]
        print(f"  {a:4d}  {v:8.4f}")

    print(f"\nValidation with N={VAL_N}...")
    t0 = time.time()
    ages = sorted(targets.keys())
    all_results = {}
    for use_ivf in [True, False]:
        res = simulate_all_ages(ages, use_ivf, best_overall["curve"],
                                best_overall["dist_type"], N_per_age=VAL_N, seed=SEED)
        for age in ages:
            if age not in all_results:
                all_results[age] = {}
            all_results[age][use_ivf] = res[age]
    print(f"Validation time: {time.time()-t0:.1f}s")

    # Comparison table
    print(f"\n{'Age':>4} | {'1(ivf)':>12} {'1(no)':>12} | {'2(ivf)':>12} {'2(no)':>12} | {'3(ivf)':>12} {'3(no)':>12}")
    print("-" * 95)

    abs_errors = []
    for age in ages:
        parts = [f"{age:4d} |"]
        for ch in [1, 2, 3]:
            for use_ivf in [True, False]:
                target = targets[age][(ch, use_ivf)]
                sim = all_results[age][use_ivf][ch - 1]
                err = abs(sim - target)
                abs_errors.append(err)
                parts.append(f"{target*100:5.1f}/{sim*100:5.1f}")
            parts.append("|")
        print(" ".join(parts))

    print(f"\nMax absolute error:  {max(abs_errors)*100:.1f} pp")
    print(f"Mean absolute error: {np.mean(abs_errors)*100:.1f} pp")
    print(f"Validation SSE:      {sum(e**2 for e in abs_errors):.6f}")


if __name__ == "__main__":
    main()
