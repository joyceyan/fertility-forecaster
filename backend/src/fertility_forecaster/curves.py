"""Age-dependent fertility curves and adjustment factors."""

from __future__ import annotations

import numpy as np

from .models import SmokingStatus

# Wesselink et al. 2017 Table 3 fecundity ratios at age bracket midpoints.
# 18-20 assumed equal to the 21-24 reference group (FR = 1.00).
_FECUNDABILITY_AGES = np.array([21, 26, 29, 32, 35, 38, 42.5], dtype=float)
_FECUNDABILITY_FR_NULLIGRAVID = np.array([1.00, 0.88, 0.80, 0.84, 0.68, 0.51, 0.20], dtype=float)
_FECUNDABILITY_FR_GRAVID = np.array([1.00, 0.92, 0.95, 0.88, 0.96, 0.70, 0.48], dtype=float)
# Base rate of 0.23 per cycle at ages 20-30, following Habbema et al. 2015 / Leridon model.
# The PRESTO cohort (Wesselink 2017) reports ~0.25 but this likely reflects upward
# selection bias from the study enrollment criteria.
_BASE_FECUNDABILITY = 0.23
# The gravid/nulligravid divergence at older ages is real, not an artifact.
# Steiner & Jukic 2016 (DOI: 10.1016/j.fertnstert.2016.02.028) independently
# corroborates this: women who have never conceived by their late 30s likely
# include those with lower underlying fertility.

# Magnus et al. 2019 miscarriage rates, flattened below age 25.
# The original study shows elevated rates for women <25 (15.8% at <20, 11.3% at
# 20-24), but this likely reflects social confounders (unplanned pregnancies,
# lifestyle factors) rather than biology. Our target users are actively planning
# pregnancies, so we use the 25-29 rate (9.8%) as a floor for all ages under 25.
_MISCARRIAGE_AGES = np.array([18.0, 27.0, 32.0, 37.0, 42.0, 47.5], dtype=float)
_MISCARRIAGE_RATES = np.array([0.098, 0.098, 0.108, 0.167, 0.322, 0.536], dtype=float)

OOCYTE_SURVIVAL_RATE = 0.785  # Hirsch et al. 2024

# Age-dependent cumulative probability of permanent sterility
# From Habbema et al. 2015 / Leridon model
_STERILITY_AGES = np.array([20, 25, 30, 35, 38, 40, 42, 45], dtype=float)
_STERILITY_RATES = np.array([0.005, 0.01, 0.02, 0.05, 0.10, 0.17, 0.30, 0.55], dtype=float)

# Concentration parameter for individual fecundability draws.
# Controls how much fecundability varies between couples.
# Lower = more heterogeneity, higher = more homogeneous.
# Calibrated against Habbema et al. 2015 benchmarks (90% cutoff ages
# for 1/2/3 children: 32/27/23). At concentration=5.0, model produces
# 31.6/27.7/23.9 — all within ±1 year.
FECUNDABILITY_CONCENTRATION = 5.0

# Recurrent miscarriage odds ratios
_RECURRENT_MC_OR = {0: 1.0, 1: 1.54, 2: 2.21}  # 3+ → 3.97


def draw_individual_fecundabilities(
    mean_fecund: float,
    n_couples: int,
    rng: np.random.Generator,
    cycles_tried: int = 0,
) -> np.ndarray:
    """Draw individual fecundability values from a Beta distribution.

    Each couple gets a fixed individual fecundability representing their
    inherent fertility type. If cycles_tried > 0, draws from the Bayesian
    posterior (shifted lower, reflecting that high-fecundability individuals
    would have already conceived).
    """
    alpha = mean_fecund * FECUNDABILITY_CONCENTRATION
    beta = (1.0 - mean_fecund) * FECUNDABILITY_CONCENTRATION + cycles_tried
    # Clip to minimum of 0.1 to avoid degenerate distributions
    alpha = max(alpha, 0.1)
    beta = max(beta, 0.1)
    return rng.beta(alpha, beta, size=n_couples)


def fecundability_curve(ages: np.ndarray, gravid: bool | np.ndarray = False) -> np.ndarray:
    """Monthly probability of conception by female age (natural intercourse).

    Gravidity-stratified using Wesselink 2017 fecundity ratios.
    Uses raw gravid ratios without capping — the divergence from the
    nulligravid curve at older ages is a real selection effect corroborated
    by Steiner & Jukic 2016.
    """
    ages = np.asarray(ages, dtype=float)
    nulligravid_fr = np.interp(ages, _FECUNDABILITY_AGES, _FECUNDABILITY_FR_NULLIGRAVID)
    gravid_fr = np.interp(ages, _FECUNDABILITY_AGES, _FECUNDABILITY_FR_GRAVID)
    nulligravid_rates = nulligravid_fr * _BASE_FECUNDABILITY
    gravid_rates = gravid_fr * _BASE_FECUNDABILITY
    return np.where(gravid, gravid_rates, nulligravid_rates)


def sterility_curve(ages: np.ndarray) -> np.ndarray:
    """Cumulative probability of permanent sterility by female age.

    From Habbema et al. 2015 / Leridon model. Represents irreversible inability
    to conceive naturally (e.g. premature ovarian failure, complete tubal occlusion).
    IVF bypasses most causes of natural sterility.
    """
    return np.interp(ages, _STERILITY_AGES, _STERILITY_RATES)


def miscarriage_curve(ages: np.ndarray) -> np.ndarray:
    """Probability of miscarriage given clinical pregnancy, by female age (Magnus 2019)."""
    return np.interp(ages, _MISCARRIAGE_AGES, _MISCARRIAGE_RATES)


def apply_odds_ratio(base_prob: np.ndarray | float, odds_ratio: np.ndarray | float) -> np.ndarray:
    """Apply an odds ratio to a base probability."""
    base = np.asarray(base_prob, dtype=float)
    or_ = np.asarray(odds_ratio, dtype=float)
    return (base * or_) / (1.0 - base + base * or_)


def recurrent_miscarriage_or(consecutive_miscarriages: np.ndarray) -> np.ndarray:
    """Odds ratio for recurrent miscarriage based on consecutive miscarriage count."""
    consecutive_miscarriages = np.asarray(consecutive_miscarriages, dtype=int)
    result = np.full_like(consecutive_miscarriages, 3.97, dtype=float)
    result[consecutive_miscarriages == 0] = 1.0
    result[consecutive_miscarriages == 1] = 1.54
    result[consecutive_miscarriages == 2] = 2.21
    return result


def male_age_miscarriage_or(male_ages: np.ndarray) -> np.ndarray:
    """Odds ratio for miscarriage based on male age. 1.0 if <40, 2.09 if >=40."""
    male_ages = np.asarray(male_ages, dtype=float)
    return np.where(male_ages >= 40, 2.09, 1.0)


def ivf_success_rate(ages: np.ndarray) -> np.ndarray:
    """Per-transfer live birth rate for fresh IVF, by female age at transfer."""
    ages = np.asarray(ages, dtype=float)
    conditions = [
        ages < 35,
        (ages >= 35) & (ages < 38),
        (ages >= 38) & (ages < 41),
        (ages >= 41) & (ages < 43),
        (ages >= 43) & (ages < 45),
        ages >= 45,
    ]
    choices = [0.40, 0.30, 0.20, 0.12, 0.05, 0.02]
    return np.select(conditions, choices)


def frozen_egg_per_oocyte_rate(retrieval_ages: np.ndarray) -> np.ndarray:
    """Per-oocyte live birth rate for frozen eggs, by age at retrieval (Namath et al. 2025)."""
    retrieval_ages = np.asarray(retrieval_ages, dtype=float)
    conditions = [
        retrieval_ages < 35,
        (retrieval_ages >= 35) & (retrieval_ages < 38),
        (retrieval_ages >= 38) & (retrieval_ages < 41),
        retrieval_ages >= 41,
    ]
    choices = [0.13, 0.09, 0.06, 0.04]
    return np.select(conditions, choices)


def frozen_embryo_transfer_rate(creation_ages: np.ndarray) -> np.ndarray:
    """Per-transfer live birth rate for frozen embryo transfer, by age at creation."""
    creation_ages = np.asarray(creation_ages, dtype=float)
    conditions = [
        creation_ages < 35,
        (creation_ages >= 35) & (creation_ages < 38),
        (creation_ages >= 38) & (creation_ages < 41),
        (creation_ages >= 41) & (creation_ages < 43),
        creation_ages >= 43,
    ]
    choices = [0.40, 0.30, 0.20, 0.12, 0.05]
    return np.select(conditions, choices)


def frozen_embryo_transfer_rate_pgt(creation_ages: np.ndarray) -> np.ndarray:
    """Per-transfer live birth rate for PGT-A tested (euploid) frozen embryos.

    Source: Jiang et al. 2025 (DOI: 10.1186/s13048-025-01602-9), n=1,037
    single euploid transfers. 41-42 and 43+ extrapolated downward for
    non-chromosomal factors (mitochondrial quality, epigenetics).
    """
    creation_ages = np.asarray(creation_ages, dtype=float)
    conditions = [
        creation_ages < 35,
        (creation_ages >= 35) & (creation_ages < 38),
        (creation_ages >= 38) & (creation_ages < 41),
        (creation_ages >= 41) & (creation_ages < 43),
        creation_ages >= 43,
    ]
    choices = [0.545, 0.540, 0.417, 0.350, 0.300]
    return np.select(conditions, choices)


def bmi_fecundability_fr(bmi: float | None) -> float:
    """Fecundability ratio based on BMI (McKinnon 2016)."""
    if bmi is None:
        return 1.0
    if bmi < 18.5:
        return 1.05
    if bmi < 25:
        return 1.0
    if bmi < 30:
        return 1.01
    if bmi < 35:
        return 0.98
    if bmi < 40:
        return 0.78
    if bmi < 45:
        return 0.61
    return 0.42


def bmi_ivf_adjustment(bmi: float | None) -> float:
    """IVF success adjustment for BMI. 1.0 if <30 or None, 0.85 if >=30."""
    if bmi is None or bmi < 30:
        return 1.0
    return 0.85


def smoking_fecundability_fr(status: SmokingStatus) -> float:
    """Fecundability ratio based on smoking status."""
    _FR = {
        SmokingStatus.NEVER: 1.0,
        SmokingStatus.FORMER: 0.89,
        SmokingStatus.CURRENT_OCCASIONAL: 0.88,
        SmokingStatus.CURRENT_REGULAR: 0.77,
    }
    return _FR[status]
