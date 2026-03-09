# Western Studies Estimating Fecundability and Sterility by Age

## The Question

Are there Western-population studies that, like Konishi 2021, estimate both
fecundability distributions AND sterility as separate age-dependent parameters?
Could they replace or improve our current approach?

**Short answer: No Western study directly replicates Konishi's zero-inflated
beta with age-specific (α, β, q) parameters. But several provide usable
estimates for one or both components.**

---

## Studies Reviewed

### 1. Dunson, Baird & Colombo 2004 — Best Western sterility+fecundability decomposition

**Paper:** "Increased Infertility With Age in Men and Women"
Obstetrics & Gynecology, 103(1):51-56.

**Data:** European Study of Daily Fecundability (ESDF), **782 couples** from
7 European natural family planning centers. **5,860 cycles, 433 pregnancies.**

**Model:** Bayesian mixture model separating a sterile fraction (point mass
at p=0) from a distribution of fecundability among fertile couples. Uses daily
coital records and basal body temperature to identify ovulation.

**Key findings:**

| Female age | Sterility | % infertile at 12 cycles (2x/week) |
|------------|-----------|--------------------------------------|
| 19-26      | ~1%       | 8%                                   |
| 27-34      | ~1%       | 13-14%                               |
| 35-39      | ~1%       | 18%                                  |

**The bombshell finding: sterility was constant at ~1% across all ages.**
All age-related decline was attributed to reduced per-cycle fecundability,
not increasing sterility.

Day-specific conception probabilities (on ovulation day):
- Ages 19-26: **0.25**
- Ages 35-39: **0.12** (roughly half)

**Usability for our model:**
- PRO: Only Western study with explicit sterility-fecundability decomposition
- PRO: European population, daily intercourse data (gold standard)
- CON: The ~1% constant sterility is almost certainly too low — the NFP
  population is self-selected for fertility (couples who have difficulty
  conceiving are less likely to use NFP as their primary method)
- CON: No age-specific distribution parameters (α, β) published
- CON: 782 couples is modest (though the cycle-level data is rich)
- CON: Does not provide parametric fecundability distribution by age

### 2. Leridon 2008 — Revised sterility curve (conception-only)

**Paper:** "A new estimate of permanent sterility by age: Sterility defined
as the inability to conceive" Population Studies, 62(1):15-24.

**Innovation:** Previous "sterility" estimates (Menken, Trussell & Larsen 1986;
Vincent 1950) measured inability to have a **live birth**, conflating true
sterility with age-related miscarriage. Leridon separated these, estimating
sterility as inability to **conceive at all**.

**Revised sterility values (inability to conceive):**

| Age | Leridon 2008 | Our model (Leridon/Habbema) |
|-----|-------------|----------------------------|
| 25  | **1%**      | 1%                         |
| 30  | **2%**      | 2%                         |
| 35  | **5%**      | 5%                         |
| 40  | **17%**     | 17%                        |
| 45  | **55%**     | 55%                        |

**Our model already uses the Leridon 2008 revised values.** The sterility
curve in `curves.py` matches Leridon 2008 exactly. This is reassuring — we
are NOT using the older, higher estimates.

**Usability:** We're already using this. The question is whether it's correct,
not whether to adopt it.

### 3. Eijkemans et al. 2014 — Historical validation (n=58,051)

**Paper:** "Too old to have children? Lessons from natural fertility populations"
Human Reproduction, 29(6):1304-1312.

**Data:** 58,051 women from 6 historical natural fertility populations
(France, Quebec, Germany, Netherlands, Utah, Quebec/SLSJ).

**"End of fertility" curve (age at last birth):**

| Age | Cumulative % at end of fertility |
|-----|----------------------------------|
| 25  | 4.5%                             |
| 30  | 7%                               |
| 35  | 12%                              |
| 38  | 20%                              |
| 41  | ~50%                             |

**Critical caveat:** These are NOT sterility rates. They measure when women
stop having children entirely, which includes inability to conceive AND
inability to carry to live birth. These values are necessarily **higher** than
conception-only sterility.

Habbema 2015's sensitivity analysis (SA2) used Eijkemans-derived higher
sterility values: 3% at 25, 6% at 30, 9% at 35 — roughly 2-3x our current
curve.

**Usability:**
- Provides an upper bound on sterility
- Validates that Leridon 2008 is at the low end of reasonable estimates
- Cannot be used directly as a sterility curve (conflates with miscarriage)

### 4. Rothman et al. 2013 — Danish fecundability ratios

**Paper:** "Volitional determinants and age-related decline in fecundability"
Fertility and Sterility, 99(7):1958-1964.

**Data:** Snart Gravid Danish internet-based cohort, **2,820 women** aged
20-40, trying <3 cycles. **2,075 pregnancies.**

**Fecundability ratios:**

| Age    | FR   | 95% CI      |
|--------|------|-------------|
| 20-24  | 1.00 | (ref)       |
| 25-29  | 1.03 | 0.90-1.18   |
| 30-34  | 1.05 | 0.89-1.23   |
| 35-40  | 0.77 | 0.62-0.97   |

**Does NOT separate sterility from fecundability.** Same methodology as
Wesselink (proportional probabilities model), same limitations.

**Key finding:** Fecundability was flat from 20-34, declining only at 35+.
This is more optimistic than Wesselink, where decline begins at 25.

**Usability:**
- Could serve as an alternative to Wesselink FRs
- Suffers from the same sterility contamination issue
- Less granular age groups than Wesselink (no gravid/nulligravid split)

### 5. Dunson, Colombo & Baird 2002 — Fertile-window fecundability

**Paper:** "Changes with age in the level and duration of fertility in the
menstrual cycle" Human Reproduction, 17(5):1399-1403.

**Same ESDF data** as Dunson 2004. Provides day-specific conception
probabilities but not age-specific parametric distributions.

**Usability:** Limited. Provides the fertile-window shape but not the
between-couple heterogeneity distribution we need.

### 6. Sozou & Hartshorne 2012 — Theoretical model closest to ours

**Paper:** "Time to Pregnancy: A Computational Method for Using the Duration
of Non-Conception for Predicting Conception"
PLoS ONE, 7(10):e46544.

**Model:** Beta(3, 10) for fecundability heterogeneity (mean=0.23, variance
matching Bongaarts 1975 data) + Leridon sterility as a separate mechanism.

**This is the closest published model to our approach.** Key differences:
- They use Beta(3, 10) with concentration=13; we use Beta(1.08, 3.25) with
  concentration=4.33
- They anchor at mean=0.23 (Habbema); we anchor at mean=0.25 (ASRM)
- They use Leridon sterility; we do too
- They do NOT use Wesselink FRs for age-decline (they use Leridon's own
  age-fecundability curve)

**Usability:**
- Validates the Beta+sterility architecture
- Does NOT solve the double-counting problem (they avoid it by not using
  Wesselink FRs)
- Their Beta(3, 10) has lower variance than ours, producing less heterogeneity

---

## Synthesis: Can Any of These Fix Our Double-Counting Problem?

### The core issue, restated

Our model applies Wesselink FRs (which embed some sterility) to non-sterile
couples AND applies Leridon sterility separately. This double-counts sterility
by approximately:
- Age 25: ~1% (negligible)
- Age 35: ~5%
- Age 40: ~17%
- Age 42: ~30%

### What we need to fix it

Either:
**(a)** Age-specific (α, β, q) parameters from a zero-inflated beta, estimated
on a large Western TTP sample → **Does not exist.**

**(b)** A reliable estimate of what fraction of Wesselink's age-FR decline is
due to sterility vs. fecundability decline, so we can decontaminate the FRs →
**Can be constructed from available data.**

**(c)** Age-specific fecundability decline curves for the fertile-only
subpopulation → **Dunson 2004 is the closest, but lacks parametric detail.**

### The most viable path: decontaminate Wesselink FRs (option b)

We have two independent estimates of sterility in the Wesselink population:

1. **Leridon 2008** (our current curve): 1% at 25, 5% at 35, 17% at 40
2. **Dunson 2004** (ESDF mixture model): ~1% constant across all ages

And we know that Wesselink excluded women with "history of infertility" and
required ≤3 cycles trying. This removes a fraction of sterile women.

The decontamination formula from our earlier analysis:
```
FR_fertile = FR_observed / (1 - sterility_in_wesselink_sample)
```

Where `sterility_in_wesselink_sample ≈ leridon_sterility × (1 - exclusion_fraction)`.

The key uncertainty is the exclusion fraction. With Leridon 2008 sterility:
- If ~50% of sterile women were excluded: the overcounting is as quantified above
- If ~75% were excluded: the overcounting is roughly halved

### Using Dunson's ~1% finding

Dunson's ~1% constant sterility would dramatically change the picture: if true
sterility is only ~1% at all ages, then:
- Our Leridon curve massively overestimates sterility
- But Wesselink's FRs would NOT be contaminated by sterility (since there's
  barely any sterility to contaminate)
- The double-counting problem largely disappears

**However, Dunson's 1% is almost certainly an underestimate** because:
1. NFP users are self-selected for fertility (couples struggling to conceive
   rarely rely on NFP as contraception)
2. The sample excluded couples not achieving pregnancy within 2 years
3. Only 782 couples — small for detecting rare events like sterility

### The sterility uncertainty spectrum

| Source | Sterility at age 35 | Sterility at age 40 |
|--------|---------------------|---------------------|
| Dunson 2004 (ESDF) | ~1% | ~1% |
| Leridon 2008 (revised) | 5% | 17% |
| Eijkemans 2014 (ALB) | 12% | ~35% |

Dunson is almost certainly too low (NFP selection). Eijkemans is too high
(includes miscarriage). Leridon 2008 sits in the middle and is the most
carefully constructed estimate of conception-only sterility.

### Recommendation

**No existing Western study provides a drop-in replacement for our approach.**
The most promising fix paths, in order of feasibility:

1. **Decontaminate Wesselink FRs** using Leridon 2008 sterility and an
   estimated exclusion fraction. This is a simple adjustment that addresses
   the structural flaw without requiring new external parameters:
   ```
   FR_adjusted = FR_observed / (1 - leridon_sterility × inclusion_fraction)
   ```
   where `inclusion_fraction ≈ 0.3-0.5` (fraction of truly sterile women
   who would still pass Wesselink's enrollment criteria).

2. **Use Sozou & Hartshorne's approach** — replace Wesselink FRs with
   Leridon's own age-fecundability curve (which was jointly calibrated with
   the sterility curve, avoiding double-counting). This sacrifices Wesselink's
   more recent data and gravid/nulligravid distinction.

3. **Fit a zero-inflated beta** to available Western TTP data. This would
   require access to raw TTP data (e.g., from PRESTO or Snart Gravid cohorts),
   which is not publicly available.

4. **Accept the overcounting** and document it as a known conservative bias,
   noting that it primarily affects nulligravid women aged 37+. The calibration
   against Habbema benchmarks partially compensates.
