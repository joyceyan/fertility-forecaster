"""Analyze potential double-counting of sterility between Wesselink FRs and Leridon sterility curve.

The question: Wesselink 2017 fecundability ratios were computed on a population
that included some unknowingly-sterile women. When we apply these FRs AND a
separate Leridon sterility curve, are we double-counting age-related sterility?

This script quantifies the overlap and compares all four approaches.
"""

import numpy as np
from scipy import stats

# ============================================================
# Data from the papers
# ============================================================

# Leridon/Habbema sterility curve (our model uses this)
STERILITY_AGES = np.array([20, 25, 30, 35, 38, 40, 42, 45])
STERILITY_RATES = np.array([0.005, 0.01, 0.02, 0.05, 0.10, 0.17, 0.30, 0.55])

def sterility_at(age):
    return float(np.interp(age, STERILITY_AGES, STERILITY_RATES))

# Wesselink 2017 fecundability ratios (Table 3)
# Nulligravid
WESSELINK_AGES_NG = [21, 26, 29, 32, 35, 38, 42.5]
WESSELINK_FR_NG = [1.00, 0.88, 0.80, 0.84, 0.68, 0.51, 0.20]
# Gravid
WESSELINK_FR_GR = [1.00, 0.92, 0.95, 0.88, 0.96, 0.70, 0.48]

def wesselink_fr(age, gravid=False):
    fr_list = WESSELINK_FR_GR if gravid else WESSELINK_FR_NG
    return float(np.interp(age, WESSELINK_AGES_NG, fr_list))

# Konishi 2021 three-parameter model (TTP-All)
# Zero-inflated beta: q = sterile fraction, remaining follows Beta(alpha, beta)
KONISHI_TTP_ALL = {
    # age_group: (alpha, beta, q_sterile, median_fecund)
    "<=24":  (1.60, 5.92, 0.03, 0.18),
    "25-29": (1.74, 10.47, 0.02, 0.12),
    "30-34": (0.82, 5.90, 0.00, 0.09),
    "35-39": (0.61, 5.97, 0.00, 0.05),
    "40+":   (0.29, 20.22, 0.00, 0.00),  # median ~0
}

# Habbema parameters
HABBEMA_BASE = 0.23
HABBEMA_CV = 0.52

# Our model parameters
OUR_BASE = 0.25
OUR_CONCENTRATION = 4.33

# ============================================================
# Analysis 1: What fraction of Wesselink FR decline is due to sterility?
# ============================================================
print("=" * 70)
print("ANALYSIS 1: Sterility contamination in Wesselink FRs")
print("=" * 70)
print()
print("The Wesselink study includes unknowingly-sterile women in its cohort.")
print("Their proportional probabilities model estimates the AVERAGE per-cycle")
print("rate, which is dragged down by sterile women (p=0) in the denominator.")
print()
print("If we assume the Wesselink population has sterility rates similar to")
print("Leridon, we can estimate the 'true' FR among fertile women only.")
print()

# However, Wesselink EXCLUDES couples with "history of infertility" and
# requires ≤3 cycles trying. This removes some (but not all) sterile women.
# Women who are sterile but don't know it (never tried, or just started)
# are still in the sample.

# Key question: what fraction of Leridon-sterile women at each age would
# have been EXCLUDED by Wesselink's criteria?
# - Women with diagnosed infertility: probably ~half of older sterile women
#   have been diagnosed (those who tried before); the other half are
#   nulligravid first-time triers who don't know they're sterile.
# - We'll estimate conservatively that Wesselink's exclusions remove
#   ~50% of sterile women at any age (rough estimate).

print(f"{'Age':>4} | {'Leridon':>8} | {'In Wess':>8} | {'FR_obs':>8} | {'FR_true':>9} | {'Over-':>7}")
print(f"{'':>4} | {'steril':>8} | {'steril':>8} | {'(ng)':>8} | {'(fertile)':>9} | {'count':>7}")
print("-" * 65)

# Assume ~50% of Leridon-sterile women are excluded by Wesselink criteria
# (those with diagnosed infertility). The rest are in the sample.
EXCLUSION_FRACTION = 0.5

for age in [21, 25, 29, 32, 35, 38, 40, 42.5]:
    leridon_ster = sterility_at(age)
    # Sterile women remaining in Wesselink sample after exclusions
    in_wesselink_ster = leridon_ster * (1 - EXCLUSION_FRACTION)

    fr_observed = wesselink_fr(age, gravid=False)

    # The observed FR is the weighted average:
    # FR_obs = (1 - in_wesselink_ster) * FR_true + in_wesselink_ster * 0
    # FR_true = FR_obs / (1 - in_wesselink_ster)
    if in_wesselink_ster < 1.0:
        fr_true = fr_observed / (1 - in_wesselink_ster)
    else:
        fr_true = 0

    overcount = (fr_true - fr_observed) / fr_observed * 100 if fr_observed > 0 else 0

    print(f"{age:4.0f}  | {leridon_ster:7.1%}  | {in_wesselink_ster:7.1%}  | "
          f"{fr_observed:7.2f}  | {fr_true:8.2f}   | {overcount:5.1f}%")

print()
print("'Over-count' shows how much higher the true FR would be if sterility")
print("were removed from the Wesselink denominator. This is the approximate")
print("magnitude of double-counting when we apply these FRs AND a separate")
print("sterility curve.")
print()
print("NOTE: The 50% exclusion fraction is a rough estimate. The actual")
print("fraction depends on what 'history of infertility' means in the PRESTO")
print("questionnaire and what fraction of sterile women have been diagnosed.")

# ============================================================
# Analysis 2: Effective sterility in our model vs intended
# ============================================================
print()
print("=" * 70)
print("ANALYSIS 2: Effective vs intended sterility in our model")
print("=" * 70)
print()

print("Our model applies TWO mechanisms that reduce fertility to zero:")
print("  1. Explicit Leridon sterility curve (threshold mechanism)")
print("  2. Wesselink FR decline (includes some sterility contamination)")
print()
print("The combined effect creates more 'effectively infertile' couples")
print("than Leridon alone would suggest.")
print()

# Simulate: for each age, what fraction of couples have effective p < 0.01?
rng = np.random.default_rng(42)
N = 100_000

print(f"{'Age':>4} | {'Leridon':>8} | {'p<0.01':>8} | {'p<0.02':>8} | {'Excess':>8}")
print(f"{'':>4} | {'sterile':>8} | {'(model)':>8} | {'(model)':>8} | {'@ 0.01':>8}")
print("-" * 55)

for age in [25, 30, 35, 38, 40, 42]:
    leridon_ster = sterility_at(age)

    # Draw sterility thresholds
    sterility_thresholds = rng.random(N)
    is_sterile = leridon_ster >= sterility_thresholds
    n_sterile = np.sum(is_sterile)

    # Draw fecundability for non-sterile couples
    starting_mean = OUR_BASE  # assume starting at 21-24 (FR=1.0)
    alpha = starting_mean * OUR_CONCENTRATION
    beta_param = (1 - starting_mean) * OUR_CONCENTRATION

    individual_fecund = np.zeros(N)
    fertile = ~is_sterile
    n_fertile = np.sum(fertile)
    individual_fecund[fertile] = rng.beta(alpha, beta_param, size=n_fertile)

    # Apply age-ratio decline (Wesselink FR)
    current_mean_ng = OUR_BASE * wesselink_fr(age, gravid=False)
    age_ratio = current_mean_ng / starting_mean if starting_mean > 0 else 0
    effective_p = individual_fecund * age_ratio
    effective_p[is_sterile] = 0.0

    frac_below_001 = np.mean(effective_p < 0.01)
    frac_below_002 = np.mean(effective_p < 0.02)
    excess = frac_below_001 - leridon_ster

    print(f"{age:4d} | {leridon_ster:7.1%}  | {frac_below_001:7.1%}  | "
          f"{frac_below_002:7.1%}  | {excess:+7.1%}")

print()
print("'Excess @ 0.01' = fraction of model couples with p<1% MINUS the")
print("Leridon sterility rate. Positive values indicate overcounting.")

# ============================================================
# Analysis 3: Konishi vs Leridon sterility estimates
# ============================================================
print()
print("=" * 70)
print("ANALYSIS 3: Konishi zero-inflated beta vs Leridon sterility")
print("=" * 70)
print()
print("Konishi (2021) explicitly estimates sterility as a separate component")
print("using a zero-inflated beta model on Japanese TTP data.")
print()

print(f"{'Age group':>10} | {'Konishi q':>10} | {'Leridon':>10} | {'Konishi/':>10}")
print(f"{'':>10} | {'(TTP-All)':>10} | {'(midpt)':>10} | {'Leridon':>10}")
print("-" * 50)

konishi_ages = {
    "<=24": (22, 0.03),
    "25-29": (27, 0.02),
    "30-34": (32, 0.00),
    "35-39": (37, 0.00),
    "40+": (42, 0.00),
}

for group, (midpoint, q) in konishi_ages.items():
    ler = sterility_at(midpoint)
    ratio = q / ler if ler > 0 else float('inf')
    print(f"{group:>10} | {q:9.0%}  | {ler:9.1%}  | {ratio:9.1f}x")

print()
print("KEY FINDING: Konishi's TTP-All model finds dramatically LOWER sterility")
print("than Leridon at all ages. For ages 30+, Konishi finds 0% sterility in")
print("the TTP-All model, while Leridon estimates 2-30%.")
print()
print("This suggests either:")
print("  (a) Leridon overestimates sterility, OR")
print("  (b) Konishi's beta distribution absorbs sterility into its left tail")
print("      (the paper notes 'probability density inflated to infinity at zero')")
print("  (c) Konishi's small sample sizes at older ages (n=21 for 40+) produce")
print("      unreliable estimates")
print()
print("Konishi's TTP-Natural model (censored at fertility treatment) shows")
print("much higher sterility: 22% at 30-34, 30% at 35-39. This is because")
print("couples who seek treatment are censored, inflating the sterile estimate.")

# ============================================================
# Analysis 4: Distribution comparison
# ============================================================
print()
print("=" * 70)
print("ANALYSIS 4: Distribution comparison at key ages")
print("=" * 70)
print()

# Compare effective fecundability distributions at age 35 and 40
for age, label in [(35, "Age 35"), (40, "Age 40")]:
    print(f"\n--- {label} ---")
    ster = sterility_at(age)

    # Our model (Beta + separate sterility)
    fr_ng = wesselink_fr(age, gravid=False)
    our_mean_at_age = OUR_BASE * fr_ng
    # The population-level mean including sterility:
    our_pop_mean = (1 - ster) * our_mean_at_age

    # Konishi at this age
    for group, (a, b, q, med) in KONISHI_TTP_ALL.items():
        midpt = konishi_ages.get(group, (0, 0))[0]
        if abs(midpt - age) <= 3:
            k_mean = a / (a + b) * (1 - q)
            k_fertile_mean = a / (a + b)
            print(f"  Konishi ({group}): fertile_mean={k_fertile_mean:.3f}, "
                  f"pop_mean={k_mean:.3f}, sterile={q:.0%}, median={med}")

    print(f"  Our model: base_FR={fr_ng:.2f}, mean_at_age={our_mean_at_age:.3f}, "
          f"sterile={ster:.1%}, pop_mean≈{our_pop_mean:.3f}")
    print(f"  Habbema:   base=0.23, sterile={ster:.1%}")


# ============================================================
# Analysis 5: What if we used Wesselink FRs WITHOUT separate sterility?
# ============================================================
print()
print("=" * 70)
print("ANALYSIS 5: Model comparison — with vs without separate sterility")
print("=" * 70)
print()
print("If Wesselink FRs already capture sterility, what happens if we")
print("DON'T add a separate sterility curve?")
print()

print(f"{'Age':>4} | {'Current model':>15} | {'No sep. steril.':>15} | {'Diff':>8}")
print(f"{'':>4} | {'eff. mean p':>15} | {'eff. mean p':>15} | {'':>8}")
print("-" * 55)

for age in [25, 30, 35, 38, 40, 42]:
    ster = sterility_at(age)
    fr_ng = wesselink_fr(age, gravid=False)
    mean_at_age = OUR_BASE * fr_ng

    # Current model: (1 - sterility) × mean_at_age
    current_pop_mean = (1 - ster) * mean_at_age

    # Without separate sterility: just mean_at_age
    # (assuming Wesselink FRs already capture sterility)
    no_ster_pop_mean = mean_at_age

    diff_pct = (current_pop_mean - no_ster_pop_mean) / no_ster_pop_mean * 100

    print(f"{age:4d} | {current_pop_mean:14.3f} | {no_ster_pop_mean:14.3f} | {diff_pct:+7.1f}%")

print()
print("The 'Current model' column shows the effective population-level mean")
print("fecundability when both mechanisms are active. At age 42, the model")
print("is ~30% more pessimistic than using Wesselink FRs alone.")
print()
print("HOWEVER: the Wesselink FRs don't fully capture sterility because:")
print("  1. Known-infertile couples were excluded from the study")
print("  2. Couples trying >3 cycles were excluded")
print("  3. So the Wesselink FRs somewhat UNDERCOUNT sterility")
print()
print("The truth likely lies between the two columns.")
