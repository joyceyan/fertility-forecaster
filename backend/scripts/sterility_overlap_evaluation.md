# Evaluation: Sterility Double-Counting in Fertility Forecaster

## The Core Question

Our model uses Wesselink 2017 age-fecundability ratios (FRs) for age-related
decline AND a separate Leridon/Habbema sterility curve. Are we double-counting
sterile/subfertile couples?

**Short answer: Yes, partially. The overcounting is negligible before age 30,
moderate at 35, and substantial by 42.**

---

## How Each Approach Models Fecundability + Sterility

### Approach A: Habbema/Leridon (2004/2015)

**Structure:** Truncated Normal distribution (CV=0.52, mean=0.23) for between-couple
heterogeneity + separate Leridon sterility curve.

**Key design:** The fecundability decline curve was reverse-engineered by
fitting a simulation (which includes the sterility mechanism) to published
demographic data. This means the decline curve and sterility curve were
**calibrated together** — the decline curve was implicitly adjusted to produce
correct outputs *given that* the sterility curve is also in the model.

**Double-counting risk:** Low/none. The two mechanisms are jointly calibrated.
The decline curve is not derived from observational fecundability studies that
include sterile women — it was fitted to family completion data.

**Weaknesses:**
- Truncated Normal is less theoretically motivated than Beta
  (Beta is the natural conjugate for Bernoulli trials)
- The fitted decline curve has a biologically implausible cliff at age 31
  (23% → ~9% in one year), likely an optimization artifact
- Single curve for all women (no gravid/nulligravid distinction)
- Older IVF data (Netherlands 2013)

### Approach B: Wesselink 2017 (PRESTO cohort)

**Structure:** Observational fecundability ratios from a proportional
probabilities regression model. Not a simulation model itself — provides
input data for other models.

**Study population:** 2,962 couples, trying ≤3 cycles at enrollment, no
self-reported history of infertility. Followed for up to 12 cycles.

**What the FRs measure:** The average per-cycle conception probability in
each age group relative to ages 21-24. The proportional probabilities model
does NOT separately estimate sterility — women who never conceive are simply
censored at cycle 12. This means the FRs conflate two phenomena:

1. Reduced per-cycle fecundability among fertile women
2. Increasing proportion of effectively sterile women in older age groups

**Critical detail about the study population:** Despite excluding couples
with "history of infertility," the cohort still contains unknowingly-sterile
women. A 38-year-old nulligravid woman who has never tried to conceive cannot
know she's sterile. If she enrolls in PRESTO having tried for 1 cycle, she's
in the study. During 12 cycles of follow-up, she never conceives. The
proportional probabilities model treats her as a very-low-fecundability
observation, dragging down the estimated FR for her age group.

**Estimated contamination:** Assuming roughly half of Leridon-sterile women
at each age would have been excluded by Wesselink's criteria (those with a
prior infertility diagnosis), the remaining sterile women contaminate the
FRs by approximately:
- Age 25: <1% (negligible)
- Age 35: ~2.5% (modest)
- Age 40: ~8.5% (meaningful)
- Age 42: ~17% (substantial)

### Approach C: Konishi 2021 (Zero-Inflated Beta)

**Structure:** Three-parameter model: sterile fraction q (point mass at p=0)
+ Beta(α, β) distribution for fecundability of non-sterile women. Estimated
via maximum likelihood from Japanese TTP data (n=1,264).

**Key finding:** When using TTP-All (including assisted conceptions), the
model finds essentially **0% sterility for ages 30+**. The sterile fraction
is absorbed into the Beta distribution's left tail (α < 1 at ages 30+ creates
probability density → ∞ at p=0). Only 2-3% sterility is detected at younger
ages.

The TTP-Natural model (censored at fertility treatment) finds much higher
sterility (22% at 30-34, 30% at 35-39), but the authors note this likely
overestimates sterility because censoring at treatment consultation inflates
the sterile estimate.

**Double-counting risk:** None by construction — sterility is explicitly
separated from the fecundability distribution.

**Weaknesses:**
- Small sample sizes (n=21 for 40+)
- Japanese population (potentially different fertility patterns)
- TTP-All model finds near-zero sterility at 30+, likely because the Beta
  distribution's left tail (α<1) absorbs the sterile signal rather than
  the zero-inflation component capturing it
- Parameters not validated against family completion data

### Approach D: Fertility Forecaster (current)

**Structure:** Beta(1.08, 3.25) for individual fecundability heterogeneity
(drawn only for non-sterile couples) + Leridon sterility curve + Wesselink
age-ratio decline applied to individual fecundabilities.

**Double-counting mechanism:** The Wesselink FRs were computed on a
population containing unknowingly-sterile women. At older ages, sterile
women drag down the observed FRs. We then apply these already-partially-
sterility-adjusted FRs to the fecundability of **non-sterile** couples,
AND separately assign ~17% of couples at age 40 to be sterile.

**Quantified overcounting (effective pop-mean fecundability):**

| Age | With both mechanisms | Wesselink FRs only | Overcounting |
|-----|---------------------|--------------------|--------------|
| 25  | 0.224               | 0.226              | -1%          |
| 30  | 0.199               | 0.203              | -2%          |
| 35  | 0.162               | 0.170              | -5%          |
| 38  | 0.115               | 0.128              | -10%         |
| 40  | 0.077               | 0.093              | -17%         |
| 42  | 0.041               | 0.059              | -30%         |

**Mitigating factors:**
1. Wesselink excludes known-infertile couples, reducing contamination
2. The ≤3 cycle enrollment criterion selects for early-stage triers
3. The concentration parameter (4.33) was calibrated against Habbema
   benchmarks, partially compensating for the overcounting
4. The sterility-first draw (sterile couples don't participate in the
   Beta draw) prevents some theoretical double-counting

**Net effect:** The model is somewhat too pessimistic for older nulligravid
women (37+). The calibration partially compensates by producing a wider
Beta distribution (CV=0.75 vs Habbema's 0.52), which increases the
proportion of high-fertility couples and partially offsets the excess
low-fertility/sterile couples. But this is an imperfect correction since
a scalar concentration parameter cannot fix an age-dependent structural bias.

---

## Ranking by Correctness

### 1. Konishi's zero-inflated Beta — Best theoretical framework

**Why:** Cleanly separates sterile (p=0) from subfertile (Beta) — double-
counting is impossible by construction. The Beta distribution is the natural
conjugate prior for Bernoulli success rates. Maximum likelihood estimation
from observational TTP data.

**Caveats:** Small samples at older ages make parameter estimates unreliable
(n=21 for 40+). Japanese population. The TTP-All model's zero sterility
finding at 30+ is suspicious — likely means the Beta's left tail (α<1)
is absorbing the sterile signal rather than the zero-inflation capturing
it. This suggests the framework is correct but the specific estimation
may have identifiability issues between "very low fecundability" and
"sterile."

### 2. Habbema/Leridon — Best validated against real-world outcomes

**Why:** The fecundability decline curve and sterility curve were jointly
calibrated against demographic data. Even if the individual components
have overlap in principle, the **combined output** matches observed family
completion rates. This is the only approach validated against multi-child
longitudinal outcomes.

**Caveats:** The decline curve's biologically implausible shape (cliff at
age 31) suggests it's absorbing artifacts from the optimization. The
truncated Normal has no theoretical justification over the Beta. No
gravid/nulligravid distinction. Older data sources.

### 3. Fertility Forecaster — Best data, structural flaw

**Why:** Uses the most recent and detailed observational data (Wesselink
2017 PRESTO cohort, SART 2023, Magnus 2019). The gravid/nulligravid
distinction is a genuine improvement. Beta distribution is well-motivated.
Calibrated against Habbema benchmarks (MAE=0.92 years).

**Caveats:** The structural overlap between Wesselink FRs and the Leridon
sterility curve creates age-dependent pessimism that cannot be fully
corrected by a single concentration parameter. At age 42 (nulligravid),
the effective overcounting is approximately 20-30%.

### 4. Wesselink FRs alone — Useful data, cannot stand alone

**Why not a complete model:** FRs are relative measures that conflate
two distinct mechanisms (fecundability decline and sterility). They
cannot be used directly in a Monte Carlo simulation that needs to
separately model whether a couple is sterile (relevant for IVF bypass)
vs. subfertile.

**Value:** Provides the best available age-decline data for the fertile
subpopulation, IF properly decontaminated for the sterility component.

---

## Key Insight

The fundamental tension is between two desiderata:

1. **Decomposition:** A simulation needs sterility and fecundability as
   separate mechanisms (because IVF bypasses sterility but not low
   fecundability).

2. **Consistency:** Observational data (Wesselink) measures the combined
   effect. Using it for one component without adjusting for the other
   creates double-counting.

The correct approach is either:
- **(a)** Use a zero-inflated Beta (Konishi framework) with age-dependent
  parameters estimated from TTP data, keeping sterility as the explicit
  zero-inflation component.
- **(b)** Use Wesselink FRs but **decontaminate** them by dividing by
  (1 - estimated_sterility_in_wesselink_sample) before applying to non-
  sterile couples in the simulation.
- **(c)** Jointly calibrate both mechanisms against outcome data (the
  Habbema approach), accepting that the individual components may not
  have clean interpretations.

Our current model does none of these — it takes the Wesselink FRs at
face value and adds a sterility curve on top. The calibration against
Habbema benchmarks provides a partial correction, but one that is
structurally imperfect.
